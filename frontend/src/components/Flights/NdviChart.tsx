import { useQuery } from '@tanstack/react-query'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from 'recharts'
import { api } from '../../api/client'
import type { NdviHistoryPoint } from '../../types'

export default function NdviChart({ fieldId }: { fieldId: string }) {
  const { data: history = [] } = useQuery<NdviHistoryPoint[]>({
    queryKey: ['ndvi-history', fieldId],
    queryFn: () => api.get(`/fields/${fieldId}/ndvi-history`).then((r) => r.data),
  })

  if (history.length === 0) return null

  if (history.length < 2) {
    return (
      <div style={{ padding: '8px 0', color: '#888', fontSize: 12 }}>
        Недостатньо даних для динаміки NDVI (потрібно ≥ 2 польоти)
      </div>
    )
  }

  const chartData = history.map((h) => ({
    date: new Date(h.flown_at).toLocaleDateString('uk-UA', { day: '2-digit', month: '2-digit' }),
    NDVI: h.ndvi_mean != null ? +h.ndvi_mean.toFixed(4) : null,
    EVI: h.evi_mean != null ? +h.evi_mean.toFixed(4) : null,
  }))

  return (
    <div style={{ marginTop: 8, marginBottom: 4 }}>
      <div style={{ fontWeight: 600, fontSize: 13, marginBottom: 6 }}>Динаміка індексів</div>
      <ResponsiveContainer width="100%" height={150}>
        <LineChart data={chartData} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey="date" tick={{ fontSize: 10 }} />
          <YAxis domain={['auto', 'auto']} tick={{ fontSize: 10 }} />
          <Tooltip formatter={(v: number) => v?.toFixed(4)} />
          <Legend iconSize={10} wrapperStyle={{ fontSize: 11 }} />
          <Line type="monotone" dataKey="NDVI" stroke="#4caf50" strokeWidth={2} dot={{ r: 3 }} connectNulls />
          <Line type="monotone" dataKey="EVI" stroke="#2196f3" strokeWidth={2} dot={{ r: 3 }} strokeDasharray="4 2" connectNulls />
        </LineChart>
      </ResponsiveContainer>
    </div>
  )
}
