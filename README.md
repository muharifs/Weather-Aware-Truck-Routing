# Weather-Aware Truck Routing

Frontend React (Vite) + backend Django REST Framework + MySQL.

```
backend/    # Django + DRF
frontend/   # React + Vite + Tailwind + shadcn/ui
```

## Prasyarat
Python 3.11+, Node.js 20+, MySQL 8.

## Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate            # Windows (Linux/Mac: source venv/bin/activate)
pip install -r requirements.txt
cp .env.example .env             # lalu isi DB_USER / DB_PASSWORD
```
Buat database (nama sesuai `DB_NAME`):
```sql
CREATE DATABASE weather_truck_routing CHARACTER SET utf8mb4;
```
Jalankan:
```bash
python manage.py migrate
python manage.py runserver       # http://localhost:8000/api/health/
pytest                           # menjalankan test
```

## Frontend
```bash
cd frontend
npm install
cp .env.example .env             # VITE_API_BASE_URL menunjuk ke backend
npm run dev                      # http://localhost:5173
```
Halaman awal menampilkan peta dan status backend dari `GET /api/health/`.
