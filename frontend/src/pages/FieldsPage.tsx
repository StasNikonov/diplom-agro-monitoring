import { useQuery } from '@tanstack/react-query'
import { api } from '../api/client'
import useAppStore from '../store/useAppStore'
import Sidebar from '../components/Layout/Sidebar'
import TopBar from '../components/Layout/TopBar'
import MapView from '../components/Map/MapView'
import type { Field, FieldMarker } from '../types'

export default function FieldsPage() {
  const { selectedFieldId, selectedFlightId, activeLayer } = useAppStore()

  const { data: fields = [] } = useQuery<Field[]>({
    queryKey: ['fields'],
    queryFn: () => api.get('/fields').then((r) => r.data),
  })

  const { data: markers = [] } = useQuery<FieldMarker[]>({
    queryKey: ['markers', selectedFieldId],
    queryFn: () => api.get(`/fields/${selectedFieldId}/markers`).then((r) => r.data),
    enabled: !!selectedFieldId,
  })

  const field = fields.find((f) => f.id === selectedFieldId) ?? null

  return (
    <div className="app-layout">
      <TopBar />
      <div className="main-area">
        <Sidebar />
        <div className="map-area">
          <MapView
            field={field}
            flightId={selectedFlightId}
            activeLayer={activeLayer}
            orthoBbox={null}
            anomalies={[]}
            markers={markers}
          />
        </div>
      </div>
    </div>
  )
}
