# Route plan API contract

`POST /api/v1/routes/plan` plans up to 3 routes, each annotated with weather checkpoints and risk.

The JSON files in this folder are the shared source of truth for backend and frontend:

| File | Meaning |
|---|---|
| `request.json` | Example request |
| `response-200.json` | Real response captured from the backend (Dallas to Denver) |
| `error-*.json` | One example body per error code |

Backend tests check the shape of real responses against these fixtures. The TypeScript types in
`frontend/src/types/routes.ts` mirror them. Change the contract in both places together.
The departure time inside `response-200.json` is a past date once the fixture ages; that is expected.

## Field semantics

- Rounding: `distance_mi`, `mile`, `avg_risk_score`, `severe_miles`, `high_miles` use 1 decimal; `duration_min` is an
  integer; `lat`/`lng` use 5 decimals.
- `geometry`: Google encoded polyline, precision 5.
- Time zones: checkpoint `eta` uses the local zone at the checkpoint; `arrival_time` uses the destination's zone
  (it equals the last checkpoint's `eta`).
- Checkpoints: one every `checkpoint_interval_mi`, starting at mile = interval (never mile 0). The last checkpoint is
  always the destination. `index` starts at 1.
- Risk levels and scores: `LOW` 0, `MODERATE` 1, `HIGH` 2, `SEVERE` 3, `NO_TRAVEL` 4.
- `risk.reasons` is an empty list for `LOW` checkpoints.
- `summary.severe_miles` / `high_miles`: sum of the segment lengths (distance from the previous checkpoint) whose
  checkpoint level is exactly `SEVERE` / `HIGH`.
- `routes` holds 1 to 3 routes sorted from most to least recommended; the first entry is the recommended one.
  `id` follows the provider order (`route_1`, `route_2`, ...), so the recommended route is not always `route_1`.
- `error.details` is only filled for `VALIDATION_ERROR` (`{field: [messages]}`); it is `{}` for other errors.

## Recommendation rule

1. Routes with `has_no_travel: true` rank last (only chosen if every route has it).
2. Then ascending by `severe_miles`, `high_miles`, `avg_risk_score`, `duration_min`.
3. `recommendation_reason` = `Severe {severe_miles} mi, High {high_miles} mi, rata-rata risiko {avg_risk_score}, {duration_min} menit`.

## Risk rules

Defined in `backend/routing/risk.py` (single place to tune).

| Factor | LOW | MODERATE | HIGH | SEVERE | NO_TRAVEL |
|---|---|---|---|---|---|
| Wind (mph) | < 20 | 20-34 | 35-44 | 45-59 | >= 60 |
| Rain (in/hr) | < 0.10 | 0.10-0.29 | 0.30-0.49 | >= 0.50 | - |
| Snow (in/hr) | 0 | > 0 to < 0.25 | 0.25-0.49 | 0.50-0.99 | >= 1.00 |

Wind of 35-44 mph with `load_weight_lb` > 40,000 raises the wind level to `SEVERE`. The checkpoint level is the
highest level across factors. These thresholds are a proposal pending product-owner confirmation.

## External services and decisions

| Need | Service | Notes |
|---|---|---|
| Geocoding | Nominatim | 1 request/second (enforced in the client), results cached 24 h |
| Routing | OSRM public server (`router.project-osrm.org`) | No API key. Car profile (no truck profile). |
| Weather | Open-Meteo | No API key. Hourly data, one batched request per plan, cached 30 min |

**Decision (Stage 1 finding):** the OSRM public server returned at most **2** routes (1 main + 1 alternative) for every
city pair tried (Dallas-Denver, Dallas-Memphis, Chicago-Detroit, ...), even when asked for 3. Therefore the API returns
**1 to 3 routes**: as many as the provider gives. To get a third route or a truck profile, implement another class with
the same `routes(origin, destination)` interface (for example OpenRouteService `driving-hgv`, which needs an API key)
and use it in `backend/routing/views.py`.
