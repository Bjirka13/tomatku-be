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

```json
{
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
		"scan_id": "<uuid>",
		"detection_id": "<uuid>"
	}
}
```

Gunakan `data.prediction.boxes` untuk menggambar bounding box di atas gambar. Koordinat box adalah piksel pada gambar asli, sehingga frontend perlu menyesuaikan skalanya saat gambar ditampilkan dengan ukuran berbeda. URL gambar tersimpan ada di `data.prediction.image_path`. Persentase confidence dan severity menggunakan rentang `0` sampai `100`.

Gambar yang bukan JPEG/PNG, rusak, atau melebihi batas ukuran menghasilkan HTTP `400`; validasi request menghasilkan `422`; kegagalan inferensi, storage, atau database menghasilkan `500`.

## Endpoint yang Belum Tersedia

- Endpoint Realtime-Detection (api/scan)
perlu threshold untuk filtering frame yg dihasilkan model

## Pekerjaan Berikutnya
- Integrasikan frontend untuk mengirim gambar, menampilkan klasifikasi/confidence/severity, dan menggambar bounding box.
- Evaluasi crop severity tetap dan gunakan bounding box model agar perhitungan lebih sesuai dengan posisi daun.
- Rapikan konfigurasi deployment backend.