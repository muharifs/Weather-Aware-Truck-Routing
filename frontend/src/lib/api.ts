import axios from 'axios'
import type { ApiErrorBody, ApiErrorCode, PlanRequest, PlanResponse } from '@/types/routes'

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL,
})

export class PlanError extends Error {
  code: ApiErrorCode
  details: Record<string, string[]>

  constructor(code: ApiErrorCode, message: string, details: Record<string, string[]> = {}) {
    super(message)
    this.code = code
    this.details = details
  }
}

// Plain-language messages shown to the user for each error code.
export const ERROR_MESSAGES: Record<ApiErrorCode, string> = {
  VALIDATION_ERROR: 'Periksa kembali isian formulir.',
  LOCATION_NOT_FOUND: 'Alamat asal atau tujuan tidak ditemukan. Coba tulis lebih lengkap, misalnya "Dallas, TX".',
  NO_ROUTE_FOUND: 'Tidak ada rute darat antara asal dan tujuan.',
  FORECAST_UNAVAILABLE: 'Prakiraan cuaca belum tersedia untuk waktu tiba. Coba waktu berangkat yang lebih dekat.',
  RATE_LIMITED: 'Kuota layanan eksternal sedang habis. Coba lagi beberapa saat lagi.',
  UPSTREAM_ERROR: 'Layanan rute atau cuaca sedang bermasalah. Coba lagi nanti.',
  NETWORK_ERROR: 'Tidak dapat terhubung ke server. Pastikan backend berjalan.',
}

export async function planRoutes(request: PlanRequest): Promise<PlanResponse> {
  try {
    const response = await api.post<PlanResponse>('/v1/routes/plan', request)
    return response.data
  } catch (error) {
    if (axios.isAxiosError<ApiErrorBody>(error) && error.response?.data?.error) {
      const { code, message, details } = error.response.data.error
      throw new PlanError(code, message, details)
    }
    throw new PlanError('NETWORK_ERROR', ERROR_MESSAGES.NETWORK_ERROR)
  }
}
