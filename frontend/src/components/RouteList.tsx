import { Badge } from '@/components/ui/badge'
import { Card, CardContent } from '@/components/ui/card'
import { formatDuration, formatLocalTime, RISK_COLORS, RISK_LABELS } from '@/lib/format'
import { cn } from '@/lib/utils'
import type { PlanResponse } from '@/types/routes'

type Props = {
  plan: PlanResponse
  selectedId: string
  onSelect: (id: string) => void
}

export function RouteList({ plan, selectedId, onSelect }: Props) {
  return (
    <div className="flex flex-col gap-2">
      <p className="rounded-lg bg-muted p-2 text-sm">
        <strong>Rekomendasi:</strong> {plan.recommendation_reason}
      </p>
      {plan.routes.map((route) => {
        const recommended = route.id === plan.recommended_route_id
        const { summary } = route
        return (
          <button
            key={route.id}
            type="button"
            onClick={() => onSelect(route.id)}
            aria-pressed={route.id === selectedId}
            className="text-left"
          >
            <Card className={cn('transition-colors', route.id === selectedId && 'ring-2 ring-primary')}>
              <CardContent className="flex flex-col gap-1 text-sm">
                <div className="flex items-center justify-between">
                  <span className="font-medium">{route.id.replace('route_', 'Rute ')}</span>
                  <span className="flex gap-1">
                    {recommended && <Badge>Direkomendasikan</Badge>}
                    <Badge
                      variant="outline"
                      style={{ borderColor: RISK_COLORS[summary.max_risk_level], color: RISK_COLORS[summary.max_risk_level] }}
                    >
                      Maks: {RISK_LABELS[summary.max_risk_level]}
                    </Badge>
                  </span>
                </div>
                <div>{route.distance_mi} mil · {formatDuration(route.duration_min)}</div>
                <div>Tiba: {formatLocalTime(route.arrival_time)}</div>
                <div className="text-muted-foreground">
                  Parah {summary.severe_miles} mil · Tinggi {summary.high_miles} mil · Rata-rata risiko {summary.avg_risk_score}
                </div>
                {summary.has_no_travel && <div className="font-medium text-destructive">Ada titik dengan status dilarang jalan</div>}
              </CardContent>
            </Card>
          </button>
        )
      })}
    </div>
  )
}
