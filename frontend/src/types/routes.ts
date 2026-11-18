// Mirrors the contract in docs/api/routes-plan (keep both in sync).

export type RiskLevel = 'LOW' | 'MODERATE' | 'HIGH' | 'SEVERE' | 'NO_TRAVEL'

export type LatLng = { lat: number; lng: number }

export type PlanRequest = {
  origin: string | LatLng
  destination: string | LatLng
  departure_time: string // ISO 8601 with time zone
  load_weight_lb: number
  checkpoint_interval_mi?: 10 | 25 | 50
}

export type Checkpoint = {
  index: number
  mile: number
  lat: number
  lng: number
  eta: string
  weather: { wind_mph: number; rain_in_hr: number; snow_in_hr: number }
  risk: { level: RiskLevel; score: number; reasons: string[] }
}

export type RouteSummary = {
  severe_miles: number
  high_miles: number
  avg_risk_score: number
  max_risk_level: RiskLevel
  has_no_travel: boolean
}

export type Route = {
  id: string
  distance_mi: number
  duration_min: number
  arrival_time: string
  geometry: string // encoded polyline, precision 5
  summary: RouteSummary
  checkpoints: Checkpoint[]
}

export type PlanResponse = {
  recommended_route_id: string
  recommendation_reason: string
  routes: Route[]
}

export type ApiErrorCode =
  | 'VALIDATION_ERROR'
  | 'LOCATION_NOT_FOUND'
  | 'NO_ROUTE_FOUND'
  | 'FORECAST_UNAVAILABLE'
  | 'RATE_LIMITED'
  | 'UPSTREAM_ERROR'
  | 'NETWORK_ERROR'

export type ApiErrorBody = {
  error: { code: ApiErrorCode; message: string; details: Record<string, string[]> }
}
