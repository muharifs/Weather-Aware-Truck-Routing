import dayjs from 'dayjs'
import type { RiskLevel } from '@/types/routes'

export const RISK_COLORS: Record<RiskLevel, string> = {
  LOW: '#16a34a',
  MODERATE: '#ca8a04',
  HIGH: '#ea580c',
  SEVERE: '#dc2626',
  NO_TRAVEL: '#450a0a',
}

export const RISK_LABELS: Record<RiskLevel, string> = {
  LOW: 'Rendah',
  MODERATE: 'Sedang',
  HIGH: 'Tinggi',
  SEVERE: 'Parah',
  NO_TRAVEL: 'Dilarang jalan',
}

/** Show an ISO time as the clock time written in the string (the local time at that place), with its UTC offset. */
export function formatLocalTime(iso: string): string {
  return `${dayjs(iso.slice(0, 19)).format('ddd D MMM, HH:mm')} (UTC${iso.slice(-6)})`
}

export function formatDuration(minutes: number): string {
  const hours = Math.floor(minutes / 60)
  const rest = minutes % 60
  return hours > 0 ? `${hours} j ${rest} m` : `${rest} m`
}

/** Decode a Google encoded polyline (precision 5) into [lng, lat] pairs for GeoJSON. */
export function decodePolyline(encoded: string): [number, number][] {
  const coordinates: [number, number][] = []
  let index = 0
  let lat = 0
  let lng = 0
  const readValue = () => {
    let result = 0
    let shift = 0
    let byte: number
    do {
      byte = encoded.charCodeAt(index++) - 63
      result |= (byte & 0x1f) << shift
      shift += 5
    } while (byte >= 0x20)
    return result & 1 ? ~(result >> 1) : result >> 1
  }
  while (index < encoded.length) {
    lat += readValue()
    lng += readValue()
    coordinates.push([lng / 1e5, lat / 1e5])
  }
  return coordinates
}
