BACKEND
Set Up Backend
# python -m pip install -r requirements.txt

Activate Backend Runtime
# python -m uvicorn main:app --reload --port 8000


Validasi Koneksi Database
# Invoke-RestMethod http://localhost:8000/health








Log Progress:

BACKEND -> DATABASE
- create db [done]
- create db & test koneksi [done]
- create bucket on supabase for image storage [done]

MODEL -> BACKEND -> DATABASE
# Database
- Connect lokal DB to supabase bucket storage

# Artifact
- add model output [done]
- definisi pipeline untuk external preprocessing function [done]

# Models
- create skema data output prediksi [done]

# Services
- create services untuk model predict [done]
- create services untuk endpoint detect [done]
- create services untuk severity function [done]

# API
detect
- create endpoint detect [done]
- testing detect on images (healthy and early bblight) [done]











Next:
# Selain testing API /api/detect

# Pastikan requirements.txt lengkap.
Dokumentasikan .env.
Pisahkan dan uji ModelService, SeverityService, serta DetectionService.
Urutan yang paling masuk akal sekarang: testing API → integrasi frontend → perbaikan crop berbasis bounding box.

# Integrasi frontend
Kirim gambar ke /api/detect.
Tampilkan classification, confidence, severity.
Gambar bounding box berdasarkan data.prediction.boxes.


# Perbaiki metode crop severity
Saat ini memakai crop tetap [0, 650, 500, 1300].
Lebih baik severity dihitung dari area bounding box hasil YOLO agar cocok dengan berbagai posisi daun.
Rapikan deployment backend