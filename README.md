# TomatKU Backend

Backend FastAPI untuk mendeteksi kondisi daun tomat, menghitung tingkat keparahan, menyimpan gambar ke Supabase Storage, dan mencatat hasil scan ke PostgreSQL.

## Fitur

- Validasi status API dan koneksi database: `GET /health`.
- Deteksi penyakit: `POST /api/detect`.
- Histori deteksi: `POST /api/history`.
- Klasifikasi `healthy`, `early_blight`, atau `unknown`, & confidence dan bounding box.
- Perhitungan severity (`ringan`, `sedang`, atau `parah`) dan persentasenya. Untuk klasifikasi `healthy`, severity bernilai `null`.
- Upload gambar ke Supabase Storage dan penyimpanan hasil deteksi ke database.

## Persiapan

1. Set Up Backend
python -m pip install -r requirements.txt

2. Activate Backend Runtime
python -m uvicorn main:app --reload --port 8000

3. Validasi Koneksi Database
Invoke-RestMethod http://localhost:8000/health

URL: `http://localhost:8000/docs`.


## Endpoint Frontend

Base URL lokal: `http://localhost:8000`
Origin frontend lokal `http://localhost:5173` dan `http://127.0.0.1:5173`

| Method | Endpoint | Kegunaan |
| --- | --- | --- |
| `GET` | `/health` | Memeriksa API dan status koneksi database. |
| `POST` | `/api/detect` | Mengirim gambar untuk dideteksi dan menyimpan hasil scan. |

### `GET /health`

Contoh respons:

```json
{
	"status": "ok",
	"service": "tomatku-be",
	"database": "ok"
}
```

Nilai `database` dapat berupa `ok` atau `unavailable`. Endpoint ini tetap mengembalikan status API `ok` saat database tidak tersedia.

### `POST /api/detect`

Kirim tepat satu dari `image_base64` atau `image_path`. Untuk frontend browser, gunakan `image_base64` berupa data URL JPEG atau PNG, misalnya `data:image/jpeg;base64,...`. `image_path` hanya untuk file yang dapat diakses langsung oleh proses backend. Ukuran gambar maksimum default adalah 5 MB (5.000.000 byte) dan dapat diubah melalui `MAX_IMAGE_SIZE_BYTES`.

## Realtime Target
Request foto biasa dapat menghilangkan `mode` (default `capture`). Untuk frame realtime, kirim `mode: "realtime"` dan `stream_id` yang stabil selama stream berjalan. Backend hanya menyimpan satu frame per stream dalam cooldown default 3 detik; ubah dengan env `REALTIME_CAPTURE_COOLDOWN_SECONDS`. Cooldown diterapkan setelah inferensi, sehingga membatasi upload dan penulisan DB, bukan jumlah inferensi.

```json
{
	"image_base64": "data:image/jpeg;base64,<base64-image-data>"
}
```

Contoh request realtime:

```json
{
	"mode": "realtime",
	"stream_id": "camera-1",
	"image_base64": "data:image/jpeg;base64,<base64-image-data>"
}
```

Contoh respons sukses, disederhanakan:

```json
{
	"status": "success",
	"data": {
		"prediction": {
			"classification": "early_blight",
			"confidence_pct": 91.23,
			"image_path": "https://...",
			"severity_level": "sedang",
			"severity_pct": 18.4,
			"boxes": [
				{
					"x1": 120.0,
					"y1": 80.0,
					"x2": 420.0,
					"y2": 360.0,
					"classification": "early_blight",
					"confidence_pct": 91.23
				}
			],
			"source": "model"
		},
		"saved": true,
		"scan": {
			"id": "<uuid>",
			"detection_mode": "capture",
			"stream_id": null
		},
		"detection": {
			"id": "<uuid>",
			"classification": "early_blight",
			"confidence_pct": 91.23,
			"image_path": "https://...",
			"severity_level": "sedang",
			"severity_pct": 18.4
		}
	}
}
```

Gunakan `data.prediction.boxes` untuk menggambar bounding box di atas gambar. Koordinat box adalah piksel pada gambar asli, sehingga frontend perlu menyesuaikan skalanya saat gambar ditampilkan dengan ukuran berbeda. URL gambar tersimpan ada di `data.prediction.image_path`. Persentase confidence dan severity menggunakan rentang `0` sampai `100`.

Frame realtime yang masih dalam cooldown tetap mengembalikan hasil prediksi, dengan `data.saved: false`, `data.reason: "cooldown"`, dan `data.detection: null`; gambar dan hasilnya tidak ditambahkan ke history. Metadata `detection_mode` dan `stream_id` berada pada entitas scan. Terapkan perubahan skema dari `database/init.sql` sebelum mengaktifkan mode realtime.

`mode` tidak ditentukan dari format file. Endpoint ini menerima satu gambar per request; file MP4 belum didukung dan tidak otomatis dianggap realtime. Untuk realtime, client mengirim frame gambar berkala dengan `mode: "realtime"` dan `stream_id` yang sama.

Untuk menguji video MP4 lokal terhadap endpoint realtime, jalankan replay sequential berikut saat backend aktif:

```powershell
python tests/video/replay_to_api.py "tests/video/videos1.mp4" --api-url http://localhost:8000/api/detect --interval 0.7 --time-limit 60 --stream-id mp4-test-1
```

Replay mengambil frame tiap 0,7 detik, mengirim satu request pada satu waktu, dan berhenti setelah 60 detik atau video selesai. Respons mencatat jumlah frame yang tersimpan dan yang ditolak cooldown. Jalankan dengan `--dry-run` untuk memeriksa sampling tanpa memanggil API. Backend tetap memerlukan konfigurasi database dan Supabase Storage untuk menyimpan frame yang lolos.

Gambar yang bukan JPEG/PNG, rusak, atau melebihi batas ukuran menghasilkan HTTP `400`; validasi request menghasilkan `422`; kegagalan inferensi, storage, atau database menghasilkan `500`.

## Pekerjaan Berikutnya
- Integrasikan frontend untuk mengirim gambar, menampilkan klasifikasi/confidence/severity, dan menggambar bounding box.
- Evaluasi crop severity tetap dan gunakan bounding box model agar perhitungan lebih sesuai dengan posisi daun.
- Rapikan konfigurasi deployment backend.