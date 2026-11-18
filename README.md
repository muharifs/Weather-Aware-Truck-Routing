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

## Route planning API

`POST /api/v1/routes/plan` returns up to 3 routes with weather checkpoints and risk levels.
The contract, example payloads, risk rules and provider decisions are in
[docs/api/routes-plan/](docs/api/routes-plan/README.md). It uses Nominatim, OSRM and Open-Meteo
(no API keys needed). Tests mock all of them, so `pytest` needs no internet connection.

```bash
curl -X POST http://localhost:8000/api/v1/routes/plan -H "Content-Type: application/json" \
  -d '{"origin":"Dallas, TX","destination":"Denver, CO","departure_time":"<ISO time within 7 days>","load_weight_lb":42000}'
```

## Frontend
```bash
cd frontend
npm install
cp .env.example .env             # VITE_API_BASE_URL points to the backend
npm run dev                      # http://localhost:5173
```
The page has a trip form (origin, destination, departure time, load, checkpoint interval), a list of the
planned routes, and a map showing the routes and risk-colored weather checkpoints.
