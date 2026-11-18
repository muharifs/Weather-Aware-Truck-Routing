import { useEffect, useMemo, useRef, useState } from 'react'
import Map, { Layer, Marker, Popup, Source, type MapRef } from 'react-map-gl/maplibre'
import { decodePolyline, formatLocalTime, RISK_COLORS, RISK_LABELS } from '@/lib/format'
import type { Checkpoint, PlanResponse } from '@/types/routes'

type Props = {
  plan: PlanResponse | null
  selectedId: string | null
  onSelect: (id: string) => void
}

export function RouteMap({ plan, selectedId, onSelect }: Props) {
  const mapRef = useRef<MapRef>(null)
  // The popup belongs to one plan; it disappears automatically when a new plan arrives.
  const [popup, setPopup] = useState<{ plan: PlanResponse | null; checkpoint: Checkpoint } | null>(null)
  const openCheckpoint = popup && popup.plan === plan ? popup.checkpoint : null
  const setOpenCheckpoint = (checkpoint: Checkpoint | null) => setPopup(checkpoint ? { plan, checkpoint } : null)

  const lines = useMemo(
    () => (plan ? plan.routes.map((route) => ({ id: route.id, coordinates: decodePolyline(route.geometry) })) : []),
    [plan],
  )

  // Fit the map to every route whenever a new plan arrives.
  useEffect(() => {
    const all = lines.flatMap((line) => line.coordinates)
    if (all.length === 0) return
    const lngs = all.map((c) => c[0])
    const lats = all.map((c) => c[1])
    mapRef.current?.fitBounds(
      [[Math.min(...lngs), Math.min(...lats)], [Math.max(...lngs), Math.max(...lats)]],
      { padding: 60, duration: 800 },
    )
  }, [lines])

  const selected = plan?.routes.find((route) => route.id === selectedId)

  return (
    <Map
      ref={mapRef}
      initialViewState={{ longitude: -98, latitude: 38, zoom: 3.5 }}
      mapStyle="https://demotiles.maplibre.org/style.json"
      style={{ width: '100%', height: '100%' }}
      interactiveLayerIds={lines.map((line) => `line-${line.id}`)}
      onClick={(event) => {
        const hit = event.features?.[0]?.layer.id
        if (hit?.startsWith('line-')) onSelect(hit.replace('line-', ''))
      }}
    >
      {lines.map((line) => {
        const isSelected = line.id === selectedId
        const isRecommended = line.id === plan?.recommended_route_id
        return (
          <Source
            key={line.id}
            id={line.id}
            type="geojson"
            data={{ type: 'Feature', properties: {}, geometry: { type: 'LineString', coordinates: line.coordinates } }}
          >
            <Layer
              id={`line-${line.id}`}
              type="line"
              layout={{ 'line-cap': 'round', 'line-join': 'round' }}
              paint={{
                'line-color': isRecommended ? '#2563eb' : '#64748b',
                'line-width': isSelected ? 7 : isRecommended ? 5 : 3,
                'line-opacity': isSelected || isRecommended ? 0.95 : 0.6,
              }}
            />
          </Source>
        )
      })}

      {selected?.checkpoints.map((checkpoint) => (
        <Marker
          key={checkpoint.index}
          longitude={checkpoint.lng}
          latitude={checkpoint.lat}
          anchor="center"
          onClick={(event) => {
            event.originalEvent.stopPropagation()
            setOpenCheckpoint(checkpoint)
          }}
        >
          <button
            type="button"
            aria-label={`Checkpoint ${checkpoint.index}, mil ${checkpoint.mile}, risiko ${RISK_LABELS[checkpoint.risk.level]}`}
            className="size-4 cursor-pointer rounded-full border-2 border-white shadow"
            style={{ backgroundColor: RISK_COLORS[checkpoint.risk.level] }}
          />
        </Marker>
      ))}

      {openCheckpoint && (
        <Popup
          longitude={openCheckpoint.lng}
          latitude={openCheckpoint.lat}
          anchor="bottom"
          offset={12}
          closeOnClick={false}
          onClose={() => setOpenCheckpoint(null)}
        >
          <div className="flex max-w-60 flex-col gap-1 text-xs text-black">
            <strong>
              Checkpoint {openCheckpoint.index} · mil {openCheckpoint.mile}
            </strong>
            <span>ETA: {formatLocalTime(openCheckpoint.eta)}</span>
            <span>
              Angin {openCheckpoint.weather.wind_mph} mph · Hujan {openCheckpoint.weather.rain_in_hr} in/jam · Salju{' '}
              {openCheckpoint.weather.snow_in_hr} in/jam
            </span>
            <span style={{ color: RISK_COLORS[openCheckpoint.risk.level] }} className="font-semibold">
              Risiko: {RISK_LABELS[openCheckpoint.risk.level]}
            </span>
            {openCheckpoint.risk.reasons.length > 0 ? (
              <ul className="list-disc pl-4">
                {openCheckpoint.risk.reasons.map((reason) => (
                  <li key={reason}>{reason}</li>
                ))}
              </ul>
            ) : (
              <span>Tidak ada risiko cuaca signifikan.</span>
            )}
          </div>
        </Popup>
      )}
    </Map>
  )
}
