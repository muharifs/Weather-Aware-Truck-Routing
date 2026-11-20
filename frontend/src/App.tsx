import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { PlanForm } from '@/components/PlanForm'
import { RouteList } from '@/components/RouteList'
import { RouteMap } from '@/components/RouteMap'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { ERROR_MESSAGES, PlanError, planRoutes } from '@/lib/api'
import type { PlanResponse } from '@/types/routes'

export default function App() {
  const [selectedId, setSelectedId] = useState<string | null>(null)

  const mutation = useMutation<PlanResponse, PlanError, Parameters<typeof planRoutes>[0]>({
    mutationFn: planRoutes,
    onSuccess: (plan) => setSelectedId(plan.recommended_route_id),
  })

  const error = mutation.error
  const serverErrors = error?.code === 'VALIDATION_ERROR' ? error.details : {}

  return (
    <div className="flex h-screen w-screen flex-col md:flex-row">
      <aside className="flex max-h-[55vh] w-full shrink-0 flex-col gap-4 overflow-y-auto border-b p-4 md:max-h-none md:w-96 md:border-r md:border-b-0">
        <h1 className="text-lg font-semibold">Weather-Aware Truck Routing</h1>
        <PlanForm onSubmit={(request) => mutation.mutate(request)} isPending={mutation.isPending} serverErrors={serverErrors} />
        {error && (
          <Alert variant="destructive">
            <AlertTitle>Rute gagal dibuat</AlertTitle>
            <AlertDescription>{ERROR_MESSAGES[error.code] ?? error.message}</AlertDescription>
          </Alert>
        )}
        {mutation.data && selectedId && (
          <RouteList plan={mutation.data} selectedId={selectedId} onSelect={setSelectedId} />
        )}
      </aside>
      <main className="min-h-0 flex-1">
        <RouteMap plan={mutation.data ?? null} selectedId={selectedId} onSelect={setSelectedId} />
      </main>
    </div>
  )
}
