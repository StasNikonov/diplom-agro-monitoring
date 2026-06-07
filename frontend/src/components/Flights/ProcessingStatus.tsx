import { useEffect, useRef } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../../api/client'
import type { FlightStatus as FS } from '../../types'

const LABELS: Record<string, string> = {
  uploaded: 'Готовий до запуску',
  odm_queued: 'В черзі на обробку...',
  odm_done: 'Фотограмметрія завершена, розраховуємо індекси...',
  odm_failed: 'Помилка обробки',
  indices_done: 'Готово',
}

const POLLING_STATUSES: FS[] = ['odm_queued', 'odm_processing', 'odm_done']

export default function ProcessingStatus({ flightId }: { flightId: string }) {
  const qc = useQueryClient()

  const { data } = useQuery({
    queryKey: ['flight-status', flightId],
    queryFn: () => api.get(`/flights/${flightId}/status`).then((r) => r.data),
    refetchInterval: (q) => {
      const status = q.state.data?.status as FS | undefined
      return status && POLLING_STATUSES.includes(status) ? 10_000 : false
    },
  })

  const doneInvalidated = useRef(false)
  useEffect(() => {
    if (data?.status === 'indices_done' && !doneInvalidated.current) {
      doneInvalidated.current = true
      qc.invalidateQueries({ queryKey: ['flight', flightId] })
      qc.invalidateQueries({ queryKey: ['orthobbox', flightId] })
      qc.invalidateQueries({ queryKey: ['anomalies', flightId] })
    }
  }, [data?.status, flightId, qc])

  const retryMutation = useMutation({
    mutationFn: () => api.post(`/flights/${flightId}/process`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['flight-status', flightId] })
      qc.invalidateQueries({ queryKey: ['flight', flightId] })
    },
  })

  if (!data) return null

  const { status, odm_progress } = data
  const isError = status === 'odm_failed'
  const isDone = status === 'indices_done'
  const isProcessing = status === 'odm_processing'

  const label = isProcessing
    ? `Фотограмметрична обробка: ${odm_progress ?? 0}%`
    : (LABELS[status] ?? status)

  const pct = isProcessing ? (odm_progress ?? 0) : isDone ? 100 : 0

  return (
    <div style={{ padding: '12px 0' }}>
      <div
        style={{
          fontWeight: 600,
          fontSize: 13,
          color: isError ? '#f44336' : isDone ? '#2e7d32' : '#333',
        }}
      >
        {label}
      </div>
      {(isProcessing || isDone) && (
        <div className="progress-bar">
          <div className="progress-bar-fill" style={{ width: `${pct}%` }} />
        </div>
      )}
      {isError && (
        <button
          className="btn btn-primary"
          style={{ marginTop: 8 }}
          disabled={retryMutation.isPending}
          onClick={() => retryMutation.mutate()}
        >
          Повторити обробку
        </button>
      )}
    </div>
  )
}
