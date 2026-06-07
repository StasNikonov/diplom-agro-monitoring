import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { api } from '../../api/client'
import useAppStore from '../../store/useAppStore'
import type { Flight } from '../../types'
import ConfirmModal from '../ConfirmModal'

const STATUS_LABELS: Record<string, string> = {
  uploaded: 'Завантажено',
  odm_queued: 'В черзі',
  odm_processing: 'Обробка',
  odm_done: 'ODM готово',
  odm_failed: 'Помилка',
  indices_done: 'Готово',
}

export default function FlightList({ fieldId, statusFilter = 'all' }: { fieldId: string; statusFilter?: string }) {
  const navigate = useNavigate()
  const qc = useQueryClient()
  const { selectedFlightId, setSelectedFlightId, role } = useAppStore()
  const isAdmin = role === 'admin'
  const [showModal, setShowModal] = useState(false)
  const [flownAt, setFlownAt] = useState('')
  const [confirmDelete, setConfirmDelete] = useState<Flight | null>(null)

  const { data: flights = [] } = useQuery<Flight[]>({
    queryKey: ['flights', fieldId],
    queryFn: () => api.get('/flights', { params: { field_id: fieldId } }).then((r) => r.data),
  })

  const createFlight = useMutation({
    mutationFn: (payload: object) => api.post('/flights', payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['flights', fieldId] })
      qc.invalidateQueries({ queryKey: ['flights-all'] })
      setShowModal(false)
    },
  })

  const deleteFlight = useMutation({
    mutationFn: (flightId: string) => api.delete(`/flights/${flightId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['flights', fieldId] })
      qc.invalidateQueries({ queryKey: ['flights-all'] })
    },
  })

  const visibleFlights = statusFilter === 'all' ? flights : flights.filter((fl) => fl.status === statusFilter)

  return (
    <div style={{ marginTop: 8 }}>
      <h2>Польоти</h2>
      <button className="btn btn-secondary" style={{ marginBottom: 8 }} onClick={() => setShowModal(true)}>
        + Новий політ
      </button>

      {visibleFlights.map((fl) => (
        <div
          key={fl.id}
          className={`card ${selectedFlightId === fl.id ? 'active' : ''}`}
          onClick={() => { setSelectedFlightId(fl.id); navigate(`/flights/${fl.id}`) }}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <h3 style={{ margin: 0 }}>{new Date(fl.flown_at).toLocaleString('uk-UA', { dateStyle: 'short', timeStyle: 'short' })}</h3>
            {isAdmin && (
              <button
                className="btn-icon-delete"
                title="Видалити політ"
                onClick={(e) => { e.stopPropagation(); setConfirmDelete(fl) }}
              >
                ✕
              </button>
            )}
          </div>
          <div className="meta">
            <span className={`status-badge status-${fl.status}`}>
              {STATUS_LABELS[fl.status] ?? fl.status}
            </span>
          </div>
        </div>
      ))}

      {showModal && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>Новий політ</h3>
            <form
              onSubmit={(e) => {
                e.preventDefault()
                createFlight.mutate({ field_id: fieldId, flown_at: new Date(flownAt).toISOString() })
              }}
            >
              <div className="form-group">
                <label>Дата польоту</label>
                <input type="datetime-local" value={flownAt} onChange={(e) => setFlownAt(e.target.value)} required />
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <button className="btn btn-primary" type="submit">Зберегти</button>
                <button className="btn btn-secondary" type="button" onClick={() => setShowModal(false)}>Скасувати</button>
              </div>
            </form>
          </div>
        </div>
      )}

      {confirmDelete && (
        <ConfirmModal
          message={`Видалити політ від ${new Date(confirmDelete.flown_at).toLocaleString('uk-UA', { dateStyle: 'short', timeStyle: 'short' })}?`}
          onConfirm={() => { deleteFlight.mutate(confirmDelete.id); setConfirmDelete(null) }}
          onCancel={() => setConfirmDelete(null)}
        />
      )}
    </div>
  )
}
