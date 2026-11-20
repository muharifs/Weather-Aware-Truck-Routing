import dayjs from 'dayjs'
import { useState, type FormEvent } from 'react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { cn } from '@/lib/utils'
import type { LatLng, PlanRequest } from '@/types/routes'

const INTERVALS = [10, 25, 50] as const
const COORDINATES = /^\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*$/
const PICKER_FORMAT = 'YYYY-MM-DDTHH:mm'

type Props = {
  onSubmit: (request: PlanRequest) => void
  isPending: boolean
  serverErrors: Record<string, string[]>
}

/** "32.78, -96.80" becomes coordinates; anything else stays an address. */
function parseLocation(text: string): string | LatLng {
  const match = COORDINATES.exec(text)
  return match ? { lat: Number(match[1]), lng: Number(match[2]) } : text.trim()
}

export function PlanForm({ onSubmit, isPending, serverErrors }: Props) {
  const [origin, setOrigin] = useState('Dallas, TX')
  const [destination, setDestination] = useState('Denver, CO')
  const [departure, setDeparture] = useState(() => dayjs().add(1, 'hour').startOf('hour').format(PICKER_FORMAT))
  const [load, setLoad] = useState('42000')
  const [interval, setInterval] = useState<(typeof INTERVALS)[number]>(25)
  const [clientErrors, setClientErrors] = useState<Record<string, string[]>>({})

  const errors = { ...serverErrors, ...clientErrors }

  function handleSubmit(event: FormEvent) {
    event.preventDefault()
    const found: Record<string, string[]> = {}
    if (!origin.trim()) found.origin = ['Wajib diisi.']
    if (!destination.trim()) found.destination = ['Wajib diisi.']
    if (origin.trim() && origin.trim().toLowerCase() === destination.trim().toLowerCase()) {
      found.destination = ['Tidak boleh sama dengan asal.']
    }
    const weight = Number(load)
    if (!load || Number.isNaN(weight) || weight < 1 || weight > 80000) {
      found.load_weight_lb = ['Harus antara 1 dan 80000.']
    }
    if (!departure || dayjs(departure).isBefore(dayjs())) {
      found.departure_time = ['Waktu berangkat tidak boleh di masa lalu.']
    } else if (dayjs(departure).isAfter(dayjs().add(7, 'day'))) {
      found.departure_time = ['Maksimal 7 hari ke depan.']
    }
    setClientErrors(found)
    if (Object.keys(found).length > 0) return

    onSubmit({
      origin: parseLocation(origin),
      destination: parseLocation(destination),
      departure_time: dayjs(departure).format('YYYY-MM-DDTHH:mm:ssZ'),
      load_weight_lb: weight,
      checkpoint_interval_mi: interval,
    })
  }

  const field = (name: string) => errors[name]?.map((message) => (
    <p key={message} className="text-xs text-destructive">{message}</p>
  ))

  return (
    <form onSubmit={handleSubmit} className="flex flex-col gap-3" noValidate>
      <div className="flex flex-col gap-1">
        <Label htmlFor="origin">Asal</Label>
        <Input id="origin" value={origin} onChange={(e) => setOrigin(e.target.value)} aria-invalid={!!errors.origin} placeholder="Dallas, TX atau 32.78, -96.80" />
        {field('origin')}
      </div>
      <div className="flex flex-col gap-1">
        <Label htmlFor="destination">Tujuan</Label>
        <Input id="destination" value={destination} onChange={(e) => setDestination(e.target.value)} aria-invalid={!!errors.destination} placeholder="Denver, CO" />
        {field('destination')}
      </div>
      <div className="flex flex-col gap-1">
        <Label htmlFor="departure">Waktu berangkat (zona waktu perangkat Anda)</Label>
        <Input
          id="departure"
          type="datetime-local"
          value={departure}
          min={dayjs().format(PICKER_FORMAT)}
          max={dayjs().add(7, 'day').format(PICKER_FORMAT)}
          onChange={(e) => setDeparture(e.target.value)}
          aria-invalid={!!errors.departure_time}
        />
        {field('departure_time')}
      </div>
      <div className="flex flex-col gap-1">
        <Label htmlFor="load">Berat muatan (lb)</Label>
        <Input id="load" type="number" min={1} max={80000} value={load} onChange={(e) => setLoad(e.target.value)} aria-invalid={!!errors.load_weight_lb} />
        {field('load_weight_lb')}
      </div>
      <div className="flex flex-col gap-1">
        <Label>Jarak antar checkpoint (mil)</Label>
        <div className="flex gap-2" role="group" aria-label="Jarak antar checkpoint">
          {INTERVALS.map((value) => (
            <Button
              key={value}
              type="button"
              variant={interval === value ? 'default' : 'outline'}
              className={cn('flex-1')}
              aria-pressed={interval === value}
              onClick={() => setInterval(value)}
            >
              {value}
            </Button>
          ))}
        </div>
        {field('checkpoint_interval_mi')}
      </div>
      <Button type="submit" disabled={isPending}>
        {isPending ? 'Menghitung rute...' : 'Rencanakan rute'}
      </Button>
    </form>
  )
}
