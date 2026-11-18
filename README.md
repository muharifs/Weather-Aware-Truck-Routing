# Weather-Aware Truck Routing

React (Vite) frontend + Django REST Framework backend + MySQL.

```
backend/    # Django + DRF
frontend/   # React + Vite + Tailwind + shadcn/ui
```

## Prerequisites
Python 3.11+, Node.js 20+, MySQL 8.

## Backend
```bash
cd backend
python -m venv venv
venv\Scripts\activate            # Windows (Linux/Mac: source venv/bin/activate)
pip install -r requirements.txt
cp .env.example .env             # then fill in DB_USER / DB_PASSWORD
```
Create the database (the name must match `DB_NAME`):
```sql
CREATE DATABASE weather_truck_routing CHARACTER SET utf8mb4;
```
Run:
```bash
python manage.py migrate
python manage.py runserver       # http://localhost:8000/api/health/
pytest                           # run the tests
```

## Frontend
```bash
cd frontend
npm install
cp .env.example .env             # VITE_API_BASE_URL points to the backend
npm run dev                      # http://localhost:5173
```
The landing page shows a map and the backend status from `GET /api/health/`.
