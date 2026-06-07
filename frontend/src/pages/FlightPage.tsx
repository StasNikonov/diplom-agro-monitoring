import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import useAppStore from '../store/useAppStore'
import TopBar from '../components/Layout/TopBar'
import FlightUpload from '../components/Flights/FlightUpload'
import ProcessingStatus from '../components/Flights/ProcessingStatus'
import MapView from '../components/Map/MapView'
import LayerControls from '../components/Map/LayerControls'
import type { Flight, Field, AnomalyZone, FieldMarker, IndexRecommendation } from '../types'

export default function FlightPage() {
  const { flightId } = useParams<{ flightId: string }>()
  const navigate = useNavigate()
  const { activeLayer, setActiveLayer } = useAppStore()

  const [notes, setNotes] = useState('')
  const [markerMode, setMarkerMode] = useState(false)
  const [pendingMarker, setPendingMarker] = useState<{ lat: number; lng: number } | null>(null)
  const [markerNote, setMarkerNote] = useState('')

  const { data: flight } = useQuery<Flight>({
    queryKey: ['flight', flightId],
    queryFn: () => api.get(`/flights/${flightId}`).then((r) => r.data),
    enabled: !!flightId,
  })

  useEffect(() => {
    if (flight?.notes !== undefined) setNotes(flight.notes ?? '')
  }, [flight?.notes])

  const { data: field } = useQuery<Field>({
    queryKey: ['field', flight?.field_id],
    queryFn: () => api.get(`/fields/${flight!.field_id}`).then((r) => r.data),
    enabled: !!flight?.field_id,
  })

  const { data: orthoBbox } = useQuery<[number, number, number, number] | null>({
    queryKey: ['orthobbox', flightId],
    queryFn: () =>
      api.get(`/flights/${flightId}/files/orthophoto/bbox`).then((r) => r.data).catch(() => null),
    enabled: flight?.status === 'indices_done',
  })

  const { data: anomalies = [] } = useQuery<AnomalyZone[]>({
    queryKey: ['anomalies', flightId],
    queryFn: () =>
      api.get(`/flights/${flightId}/anomalies`).then((r) =>
        r.data.features.map((f: any) => ({
          ...f.properties,
          zone_geom: f.geometry,
        })),
      ),
    enabled: flight?.status === 'indices_done',
  })

  const { data: markers = [] } = useQuery<FieldMarker[]>({
    queryKey: ['markers', flight?.field_id],
    queryFn: () => api.get(`/fields/${flight!.field_id}/markers`).then((r) => r.data),
    enabled: !!flight?.field_id,
  })

  const { data: recommendations = [] } = useQuery<IndexRecommendation[]>({
    queryKey: ['recommendations', flightId],
    queryFn: () => api.get(`/flights/${flightId}/recommendations`).then((r) => r.data),
    enabled: flight?.status === 'indices_done',
  })

  const qc = useQueryClient()

  const recalcMutation = useMutation({
    mutationFn: () => api.post(`/flights/${flightId}/recalculate-anomalies`),
    onSuccess: () => {
      setTimeout(() => {
        qc.invalidateQueries({ queryKey: ['anomalies', flightId] })
      }, 3000)
    },
  })

  const recalcIndicesMutation = useMutation({
    mutationFn: () => api.post(`/flights/${flightId}/recalculate-indices`),
    onSuccess: () => {
      setTimeout(() => {
        qc.invalidateQueries({ queryKey: ['flight', flightId] })
        qc.invalidateQueries({ queryKey: ['orthobbox', flightId] })
        qc.invalidateQueries({ queryKey: ['anomalies', flightId] })
      }, 5000)
    },
  })

  const notesMutation = useMutation({
    mutationFn: (n: string) => api.patch(`/flights/${flightId}/notes`, { notes: n }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['flight', flightId] }),
  })

  const addMarkerMutation = useMutation({
    mutationFn: ({ lat, lon, note }: { lat: number; lon: number; note: string }) =>
      api.post(`/fields/${flight!.field_id}/markers`, { lat, lon, note }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['markers', flight?.field_id] })
      setPendingMarker(null)
      setMarkerNote('')
    },
  })

  const deleteMarkerMutation = useMutation({
    mutationFn: (markerId: string) =>
      api.delete(`/fields/${flight!.field_id}/markers/${markerId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['markers', flight?.field_id] }),
  })

  if (!flightId) return null

  const isDone = flight?.status === 'indices_done'
  const isUploaded = flight?.status === 'uploaded'
  const showUpload = isUploaded || !flight

  const downloadExport = async (fmt: string, filename: string) => {
    const res = await api.get(`/flights/${flightId}/export?format=${fmt}`, { responseType: 'blob' })
    const url = URL.createObjectURL(res.data)
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    setTimeout(() => URL.revokeObjectURL(url), 1000)
  }

  const downloadReport = async () => {
    try {
      const res = await api.get(`/flights/${flightId}/report`, { responseType: 'blob' })
      const blob = res.data as Blob
      if (blob.type.includes('json') || blob.type.includes('text')) {
        const text = await blob.text()
        alert(`Помилка сервера: ${text}`)
        return
      }
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `report_${flightId}.pdf`
      document.body.appendChild(a)
      a.click()
      document.body.removeChild(a)
      setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch (err: any) {
      const msg = err?.response?.data ? await new Blob([err.response.data]).text() : String(err)
      alert(`Не вдалося завантажити звіт: ${msg}`)
    }
  }

  const handleAddMarker = (lat: number, lng: number) => {
    setPendingMarker({ lat, lng })
    setMarkerMode(false)
  }

  return (
    <div className="app-layout">
      <TopBar />
      <div className="main-area">
        <div className="flight-sidebar">
          <button className="btn btn-secondary" style={{ marginBottom: 12 }} onClick={() => navigate('/')}>
            ← Назад
          </button>

          <h2 style={{ fontSize: 15, margin: '0 0 8px' }}>
            {flight
              ? new Date(flight.flown_at).toLocaleString('uk-UA', { dateStyle: 'short', timeStyle: 'short' })
              : '…'}
          </h2>

          <ProcessingStatus flightId={flightId} />

          {showUpload && <FlightUpload flightId={flightId} />}

          {isDone && (
            <>
              <LayerControls
                activeLayer={activeLayer}
                setActiveLayer={setActiveLayer}
                indexMaps={flight?.index_maps ?? []}
                hasDsm={flight?.has_dsm}
              />

<div style={{ display: 'flex', flexDirection: 'column', gap: 6, marginTop: 8 }}>
                <button className="btn btn-secondary" onClick={downloadReport}>
                  PDF-звіт
                </button>
                {!flight?.has_dsm && (
                  <button
                    className="btn btn-secondary"
                    style={{ fontSize: 11, color: '#888' }}
                    disabled={recalcIndicesMutation.isPending}
                    onClick={() => recalcIndicesMutation.mutate()}
                  >
                    {recalcIndicesMutation.isPending ? 'Обробка...' : '↻ Оновити шари'}
                  </button>
                )}
              </div>
            </>
          )}

          {recommendations.length > 0 && (
            <div style={{ marginTop: 12 }}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 6 }}>Стан посівів</div>
              {recommendations.map((rec) => {
                const bg: Record<string, string> = {
                  red: '#ffebee', orange: '#fff3e0', yellow: '#fffde7',
                  green: '#e8f5e9', darkgreen: '#e8f5e9', blue: '#e3f2fd', gray: '#f5f5f5',
                }
                const border: Record<string, string> = {
                  red: '#f44336', orange: '#ff9800', yellow: '#ffc107',
                  green: '#4caf50', darkgreen: '#2e7d32', blue: '#2196f3', gray: '#9e9e9e',
                }
                return (
                  <div key={rec.index_type} style={{ marginBottom: 8, padding: '8px 10px', borderRadius: 8, background: bg[rec.color] ?? '#f5f5f5', borderLeft: `4px solid ${border[rec.color] ?? '#9e9e9e'}` }}>
                    <div style={{ fontWeight: 700, fontSize: 12, marginBottom: 2 }}>
                      {rec.index_type}: {rec.category}
                    </div>
                    <div style={{ fontSize: 11, color: '#444', lineHeight: 1.4 }}>{rec.recommendation}</div>
                  </div>
                )
              })}
            </div>
          )}

          <div style={{ marginTop: 16 }}>
            <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 6 }}>Нотатки</div>
            <textarea
              value={notes}
              onChange={(e) => setNotes(e.target.value)}
              rows={3}
              placeholder="Додайте нотатки до польоту..."
              style={{ width: '100%', padding: '6px 8px', fontSize: 12, borderRadius: 6, border: '1px solid #ddd', resize: 'vertical' }}
            />
            <button
              className="btn btn-secondary"
              style={{ marginTop: 4, width: '100%' }}
              disabled={notesMutation.isPending}
              onClick={() => notesMutation.mutate(notes)}
            >
              {notesMutation.isPending ? 'Збереження...' : 'Зберегти нотатки'}
            </button>
          </div>

          {flight?.field_id && (
            <div style={{ marginTop: 16 }}>
              <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 6 }}>Позначки на карті</div>
              {!markerMode ? (
                <button
                  className="btn btn-secondary"
                  style={{ width: '100%', marginBottom: 6 }}
                  onClick={() => setMarkerMode(true)}
                >
                  + Додати позначку
                </button>
              ) : (
                <div style={{ fontSize: 12, color: '#555', padding: '6px 8px', background: '#e3f2fd', borderRadius: 6, marginBottom: 6 }}>
                  Клікніть на карту, щоб розмістити позначку
                  <button
                    className="btn btn-secondary"
                    style={{ marginLeft: 8, fontSize: 11, padding: '2px 6px' }}
                    onClick={() => setMarkerMode(false)}
                  >
                    Скасувати
                  </button>
                </div>
              )}

              {pendingMarker && (
                <div style={{ marginBottom: 8 }}>
                  <textarea
                    value={markerNote}
                    onChange={(e) => setMarkerNote(e.target.value)}
                    rows={2}
                    placeholder="Нотатка до позначки (необов'язково)"
                    style={{ width: '100%', padding: '6px 8px', fontSize: 12, borderRadius: 6, border: '1px solid #ddd', resize: 'none' }}
                  />
                  <div style={{ display: 'flex', gap: 6, marginTop: 4 }}>
                    <button
                      className="btn btn-primary"
                      style={{ flex: 1 }}
                      disabled={addMarkerMutation.isPending}
                      onClick={() => addMarkerMutation.mutate({ lat: pendingMarker.lat, lon: pendingMarker.lng, note: markerNote })}
                    >
                      Зберегти
                    </button>
                    <button
                      className="btn btn-secondary"
                      onClick={() => { setPendingMarker(null); setMarkerNote('') }}
                    >
                      ✕
                    </button>
                  </div>
                </div>
              )}

              {markers.length > 0 && (
                <div style={{ maxHeight: 140, overflowY: 'auto' }}>
                  {markers.map((m) => (
                    <div
                      key={m.id}
                      style={{ display: 'flex', alignItems: 'flex-start', gap: 6, padding: '4px 0', borderBottom: '1px solid #f0f0f0', fontSize: 12 }}
                    >
                      <span style={{ flex: 1, color: '#555' }}>
                        {m.note || 'Без нотатки'}
                      </span>
                      <button
                        className="btn-icon-delete"
                        onClick={() => deleteMarkerMutation.mutate(m.id)}
                      >
                        ✕
                      </button>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        <div className="map-area">
          <MapView
            field={field ?? null}
            flightId={flightId}
            activeLayer={activeLayer}
            orthoBbox={orthoBbox ?? null}
            anomalies={anomalies}
            markers={markers}
            markerMode={markerMode}
            onAddMarker={handleAddMarker}
          />
        </div>
      </div>
    </div>
  )
}
