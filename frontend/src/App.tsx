import { useQuery } from '@tanstack/react-query'
import dayjs from 'dayjs'
import Map from 'react-map-gl/maplibre'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { api } from '@/lib/api'

type Health = { status: string }

export default function App() {
  const { data, isLoading, isError, dataUpdatedAt } = useQuery({
    queryKey: ['health'],
    queryFn: async () => (await api.get<Health>('/health/')).data,
  })

  const status = isLoading ? 'Memeriksa...' : isError ? 'Backend tidak terjangkau' : data?.status

  return (
    <div className="relative h-screen w-screen">
      <Map
        initialViewState={{ longitude: 106.8456, latitude: -6.2088, zoom: 8 }}
        mapStyle="https://demotiles.maplibre.org/style.json"
        style={{ width: '100%', height: '100%' }}
      />
      <Card className="absolute left-4 top-4 w-72">
        <CardHeader>
          <CardTitle>Weather-Aware Truck Routing</CardTitle>
        </CardHeader>
        <CardContent className="text-sm">
          <p>Status backend: <strong>{status}</strong></p>
          {dataUpdatedAt > 0 && <p>Dicek: {dayjs(dataUpdatedAt).format('HH:mm:ss')}</p>}
        </CardContent>
      </Card>
    </div>
  )
}
