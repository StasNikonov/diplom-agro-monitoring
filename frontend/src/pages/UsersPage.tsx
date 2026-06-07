import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { api } from '../api/client'
import useAppStore from '../store/useAppStore'
import TopBar from '../components/Layout/TopBar'

interface UserOut {
  id: string
  username: string
  role: string
  created_at: string
}

export default function UsersPage() {
  const navigate = useNavigate()
  const role = useAppStore((s) => s.role)
  const qc = useQueryClient()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [formError, setFormError] = useState('')

  if (role !== 'admin') {
    navigate('/', { replace: true })
    return null
  }

  const { data: users = [], isLoading } = useQuery<UserOut[]>({
    queryKey: ['users'],
    queryFn: () => api.get('/users').then((r) => r.data),
  })

  const createUser = useMutation({
    mutationFn: (payload: { username: string; password: string }) =>
      api.post('/users', payload),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users'] })
      setUsername('')
      setPassword('')
      setFormError('')
    },
    onError: (err: any) => {
      setFormError(err?.response?.data?.detail ?? 'Помилка створення')
    },
  })

  const deleteUser = useMutation({
    mutationFn: (userId: string) => api.delete(`/users/${userId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['users'] }),
  })

  const handleCreate = (e: React.FormEvent) => {
    e.preventDefault()
    setFormError('')
    createUser.mutate({ username, password })
  }

  return (
    <div className="app-layout">
      <TopBar />
      <div style={{ padding: '24px 32px', maxWidth: 700, margin: '0 auto', width: '100%' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 24 }}>
          <button className="btn btn-secondary" onClick={() => navigate('/')}>
            ← Назад
          </button>
          <h2 style={{ fontSize: 20, fontWeight: 700 }}>Управління користувачами</h2>
        </div>

        <div style={{ background: '#fff', border: '1px solid #e0e0e0', borderRadius: 10, padding: 20, marginBottom: 24 }}>
          <h3 style={{ fontSize: 15, marginBottom: 16 }}>Зареєструвати співробітника</h3>
          <form onSubmit={handleCreate} style={{ display: 'flex', gap: 10, flexWrap: 'wrap', alignItems: 'flex-end' }}>
            <div style={{ flex: 1, minWidth: 160 }}>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#555', marginBottom: 4 }}>Логін</label>
              <input
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                placeholder="username"
                required
                style={{ width: '100%', padding: '8px 10px', border: '1.5px solid #ddd', borderRadius: 6, fontSize: 14 }}
              />
            </div>
            <div style={{ flex: 1, minWidth: 160 }}>
              <label style={{ display: 'block', fontSize: 12, fontWeight: 600, color: '#555', marginBottom: 4 }}>Пароль</label>
              <input
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••"
                required
                style={{ width: '100%', padding: '8px 10px', border: '1.5px solid #ddd', borderRadius: 6, fontSize: 14 }}
              />
            </div>
            <button
              type="submit"
              className="btn btn-primary"
              disabled={createUser.isPending}
              style={{ whiteSpace: 'nowrap' }}
            >
              {createUser.isPending ? 'Збереження...' : '+ Додати'}
            </button>
          </form>
          {formError && (
            <p style={{ color: '#c62828', fontSize: 13, marginTop: 8 }}>{formError}</p>
          )}
        </div>

        <div style={{ background: '#fff', border: '1px solid #e0e0e0', borderRadius: 10, overflow: 'hidden' }}>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ background: '#f8f9fa', borderBottom: '1px solid #e0e0e0' }}>
                <th style={{ padding: '10px 16px', textAlign: 'left', fontSize: 12, fontWeight: 600, color: '#555', textTransform: 'uppercase' }}>Логін</th>
                <th style={{ padding: '10px 16px', textAlign: 'left', fontSize: 12, fontWeight: 600, color: '#555', textTransform: 'uppercase' }}>Роль</th>
                <th style={{ padding: '10px 16px', textAlign: 'left', fontSize: 12, fontWeight: 600, color: '#555', textTransform: 'uppercase' }}>Зареєстровано</th>
                <th style={{ width: 48 }}></th>
              </tr>
            </thead>
            <tbody>
              {isLoading && (
                <tr><td colSpan={4} style={{ padding: 20, textAlign: 'center', color: '#888', fontSize: 13 }}>Завантаження...</td></tr>
              )}
              {!isLoading && users.length === 0 && (
                <tr><td colSpan={4} style={{ padding: 20, textAlign: 'center', color: '#888', fontSize: 13 }}>Користувачів немає</td></tr>
              )}
              {users.map((u) => (
                <tr key={u.id} style={{ borderBottom: '1px solid #f0f0f0' }}>
                  <td style={{ padding: '10px 16px', fontSize: 14, fontWeight: 500 }}>{u.username}</td>
                  <td style={{ padding: '10px 16px' }}>
                    <span style={{
                      display: 'inline-block', padding: '2px 8px', borderRadius: 10,
                      fontSize: 11, fontWeight: 600,
                      background: u.role === 'admin' ? '#e8f5e9' : '#e3f2fd',
                      color: u.role === 'admin' ? '#2e7d32' : '#1565c0',
                    }}>
                      {u.role === 'admin' ? 'Адмін' : 'Співробітник'}
                    </span>
                  </td>
                  <td style={{ padding: '10px 16px', fontSize: 12, color: '#888' }}>
                    {new Date(u.created_at).toLocaleString('uk-UA', { dateStyle: 'short', timeStyle: 'short' })}
                  </td>
                  <td style={{ padding: '10px 8px', textAlign: 'center' }}>
                    {u.role !== 'admin' && (
                      <button
                        className="btn-icon-delete"
                        title="Видалити"
                        onClick={() => deleteUser.mutate(u.id)}
                      >
                        ✕
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
