import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api/client'
import useAppStore from '../../store/useAppStore'
import type { Field, Flight } from '../../types'
import FlightList from '../Flights/FlightList'
import NdviChart from '../Flights/NdviChart'
import ConfirmModal from '../ConfirmModal'

function getBbox(boundary: any): [[number, number], [number, number]] | null {
  if (!boundary?.coordinates?.[0]) return null
  const coords: [number, number][] = boundary.coordinates[0]
  const lngs = coords.map((c) => c[0])
  const lats = coords.map((c) => c[1])
  return [
    [Math.min(...lngs), Math.min(...lats)],
    [Math.max(...lngs), Math.max(...lats)],
  ]
}

export default function Sidebar() {
  const qc = useQueryClient()
  const { selectedFieldId, setSelectedFieldId, setSelectedFlightId, setZoomToBounds, role } = useAppStore()
  const isAdmin = role === 'admin'
  const [showModal, setShowModal] = useState(false)
  const [newName, setNewName] = useState('')
  const [newArea, setNewArea] = useState('')
  const [confirmDelete, setConfirmDelete] = useState<Field | null>(null)
  const [statusFilter, setStatusFilter] = useState('all')

  const { data: fields = [] } = useQuery<Field[]>({
    queryKey: ['fields'],
    queryFn: () => api.get('/fields').then((r) => r.data),
  })

  const { data: allFlights = [] } = useQuery<Flight[]>({
    queryKey: ['flights-all'],
    queryFn: () => api.get('/flights').then((r) => r.data),
    enabled: fields.length > 0,
  })

  const createField = useMutation({
    mutationFn: (payload: object) => api.post('/fields', payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['fields'] })
      setShowModal(false)
      setNewName('')
      setNewArea('')
    },
  })

  const deleteField = useMutation({
    mutationFn: (fieldId: string) => api.delete(`/fields/${fieldId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['fields'] })
      qc.invalidateQueries({ queryKey: ['flights-all'] })
      setSelectedFieldId(null)
      setSelectedFlightId(null)
    },
  })

  const handleFieldClick = (f: Field) => {
    setSelectedFieldId(f.id)
    setSelectedFlightId(null)
    if (f.boundary) {
      const bbox = getBbox(f.boundary)
      if (bbox) setZoomToBounds(bbox)
    }
  }

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault()
    createField.mutate({ name: newName, area_ha: parseFloat(newArea) || null })
  }

  const knownFieldIds = new Set(fields.map((f) => f.id))
  const activeFlights = allFlights.filter((f) => f.field_id && knownFieldIds.has(f.field_id))

  return (
    <div className="sidebar">
      <div className="dash-stats">
        <div className="dash-stat">
          <span className="dash-stat-num">{fields.length}</span>
          <span className="dash-stat-label">Поля</span>
        </div>
        <div className="dash-stat">
          <span className="dash-stat-num">{activeFlights.length}</span>
          <span className="dash-stat-label">Польоти</span>
        </div>
      </div>

      <h2>Поля</h2>

      {isAdmin && (
        <button className="btn btn-primary" style={{ width: '100%', marginBottom: 12 }} onClick={() => setShowModal(true)}>
          + Додати поле
        </button>
      )}

      {fields.map((f) => (
        <div
          key={f.id}
          className={`card ${selectedFieldId === f.id ? 'active' : ''}`}
          onClick={() => handleFieldClick(f)}
        >
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
            <h3 style={{ margin: 0 }}>{f.name}</h3>
            {isAdmin && (
              <button
                className="btn-icon-delete"
                title="Видалити поле"
                onClick={(e) => { e.stopPropagation(); setConfirmDelete(f) }}
              >
                ✕
              </button>
            )}
          </div>
          <div className="meta">{f.area_ha ? `${f.area_ha} га` : '—'}</div>
        </div>
      ))}

      {selectedFieldId && (
        <>
          <NdviChart fieldId={selectedFieldId} />

          <div style={{ marginTop: 8, marginBottom: 4 }}>
            <select
              value={statusFilter}
              onChange={(e) => setStatusFilter(e.target.value)}
              style={{ width: '100%', padding: '6px 8px', fontSize: 12, borderRadius: 6, border: '1px solid #ddd', background: '#fff' }}
            >
              <option value="all">Всі польоти</option>
              <option value="indices_done">Готові</option>
              <option value="odm_failed">З помилкою</option>
              <option value="odm_queued">В черзі</option>
              <option value="odm_processing">Обробляються</option>
              <option value="uploaded">Завантажено</option>
            </select>
          </div>
          <FlightList fieldId={selectedFieldId} statusFilter={statusFilter} />
        </>
      )}

      {showModal && isAdmin && (
        <div className="modal-overlay" onClick={() => setShowModal(false)}>
          <div className="modal" onClick={(e) => e.stopPropagation()}>
            <h3>Нове поле</h3>
            <form onSubmit={handleCreate}>
              <div className="form-group">
                <label>Назва</label>
                <input value={newName} onChange={(e) => setNewName(e.target.value)} required />
              </div>
              <div className="form-group">
                <label>Площа (га)</label>
                <input type="number" step="0.01" value={newArea} onChange={(e) => setNewArea(e.target.value)} />
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <button className="btn btn-primary" type="submit" disabled={createField.isPending}>
                  {createField.isPending ? 'Збереження...' : 'Зберегти'}
                </button>
                <button className="btn btn-secondary" type="button" onClick={() => setShowModal(false)}>
                  Скасувати
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {confirmDelete && (
        <ConfirmModal
          message={`Видалити поле "${confirmDelete.name}" та всі його польоти?`}
          onConfirm={() => { deleteField.mutate(confirmDelete.id); setConfirmDelete(null) }}
          onCancel={() => setConfirmDelete(null)}
        />
      )}
    </div>
  )
}
