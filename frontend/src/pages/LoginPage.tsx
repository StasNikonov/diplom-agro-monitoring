import { useState } from 'react'
import { useNavigate, Navigate } from 'react-router-dom'
import { api } from '../api/client'
import useAppStore from '../store/useAppStore'

export default function LoginPage() {
  const navigate = useNavigate()
  const { token, setToken, setRole } = useAppStore()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(false)

  if (token) {
    return <Navigate to="/" replace />
  }

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')
    try {
      const form = new URLSearchParams()
      form.append('username', username)
      form.append('password', password)
      const { data } = await api.post('/auth/token', form, {
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
      })
      setToken(data.access_token)
      setRole(data.role)
      navigate('/', { replace: true })
    } catch {
      setError('Невірний логін або пароль')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="lp-root">
      <div className="lp-brand">
        <div className="lp-brand-inner">
          <div className="lp-logo">
            <svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
              <rect width="64" height="64" rx="14" fill="#ffffff22"/>
              <line x1="32" y1="54" x2="32" y2="18" stroke="#a8d5a2" strokeWidth="2.5" strokeLinecap="round"/>
              <ellipse cx="32" cy="18" rx="4.5" ry="6" fill="#f5d86e" transform="rotate(-15 32 18)"/>
              <ellipse cx="27" cy="22" rx="4" ry="5.5" fill="#f5d86e" transform="rotate(-35 27 22)"/>
              <ellipse cx="37" cy="22" rx="4" ry="5.5" fill="#f5d86e" transform="rotate(35 37 22)"/>
              <ellipse cx="24" cy="27" rx="3.5" ry="5" fill="#f5d86e" transform="rotate(-40 24 27)"/>
              <ellipse cx="40" cy="27" rx="3.5" ry="5" fill="#f5d86e" transform="rotate(40 40 27)"/>
              <line x1="32" y1="44" x2="18" y2="36" stroke="#7ec8a0" strokeWidth="2" strokeLinecap="round"/>
              <line x1="32" y1="44" x2="46" y2="36" stroke="#7ec8a0" strokeWidth="2" strokeLinecap="round"/>
              <circle cx="16" cy="35" r="4" fill="none" stroke="#7ec8a0" strokeWidth="1.5"/>
              <circle cx="48" cy="35" r="4" fill="none" stroke="#7ec8a0" strokeWidth="1.5"/>
            </svg>
          </div>
          <h1 className="lp-brand-title">Agro Monitoring</h1>
          <p className="lp-brand-sub">Система моніторингу сільськогосподарських угідь за допомогою БПЛА</p>
          <ul className="lp-features">
            <li>
              <span className="lp-feat-icon">
                <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M5.05 3.636a1 1 0 010 1.414 7 7 0 000 9.9 1 1 0 11-1.414 1.414 9 9 0 010-12.728 1 1 0 011.414 0zm9.9 0a1 1 0 011.414 0 9 9 0 010 12.728 1 1 0 11-1.414-1.414 7 7 0 000-9.9 1 1 0 010-1.414zM7.879 6.464a1 1 0 010 1.414 3 3 0 000 4.243 1 1 0 11-1.415 1.414 5 5 0 010-7.07 1 1 0 011.415 0zm4.242 0a1 1 0 011.415 0 5 5 0 010 7.072 1 1 0 01-1.415-1.415 3 3 0 000-4.242 1 1 0 010-1.415zM10 9a1 1 0 011 1v.01a1 1 0 11-2 0V10a1 1 0 011-1z" clipRule="evenodd"/></svg>
              </span>
              <span>Аналіз ортофотознімків у режимі реального часу</span>
            </li>
            <li>
              <span className="lp-feat-icon">
                <svg viewBox="0 0 20 20" fill="currentColor"><path d="M2 10a8 8 0 018-8v8h8a8 8 0 11-16 0z"/><path d="M12 2.252A8.014 8.014 0 0117.748 8H12V2.252z"/></svg>
              </span>
              <span>Розрахунок вегетаційних індексів NDVI та EVI</span>
            </li>
            <li>
              <span className="lp-feat-icon">
                <svg viewBox="0 0 20 20" fill="currentColor"><path fillRule="evenodd" d="M12 1.586l-4 4V17h8V5.586l-4-4zM3.707 4.293A1 1 0 002 5v12a1 1 0 001 1h2V5.586L3.707 4.293zM17 18a1 1 0 001-1V5a1 1 0 00-1.707-.707L15 5.586V18h2z" clipRule="evenodd"/></svg>
              </span>
              <span>Інтерактивні карти полів на основі MapLibre GL</span>
            </li>
            <li>
              <span className="lp-feat-icon">
                <svg viewBox="0 0 20 20" fill="currentColor"><path d="M2 11a1 1 0 011-1h2a1 1 0 011 1v5a1 1 0 01-1 1H3a1 1 0 01-1-1v-5zM8 7a1 1 0 011-1h2a1 1 0 011 1v9a1 1 0 01-1 1H9a1 1 0 01-1-1V7zM14 4a1 1 0 011-1h2a1 1 0 011 1v12a1 1 0 01-1 1h-2a1 1 0 01-1-1V4z"/></svg>
              </span>
              <span>Автоматичні агрономічні рекомендації</span>
            </li>
          </ul>
        </div>
      </div>

      <div className="lp-form-panel">
        <div className="lp-form-inner">
          <div className="lp-form-header">
            <h2>Вхід до системи</h2>
            <p>Введіть облікові дані для доступу до панелі моніторингу</p>
          </div>

          <form onSubmit={handleSubmit} className="lp-form">
            {error && (
              <div className="lp-error">
                <svg viewBox="0 0 20 20" fill="currentColor" width="16" height="16">
                  <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd"/>
                </svg>
                {error}
              </div>
            )}

            <div className="lp-field">
              <label htmlFor="lp-username">Логін</label>
              <div className="lp-input-wrap">
                <svg className="lp-input-icon" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M10 9a3 3 0 100-6 3 3 0 000 6zm-7 9a7 7 0 1114 0H3z" clipRule="evenodd"/>
                </svg>
                <input
                  id="lp-username"
                  name="username"
                  type="text"
                  placeholder="admin"
                  value={username}
                  onChange={(e) => setUsername(e.target.value)}
                  autoFocus
                  autoComplete="username"
                />
              </div>
            </div>

            <div className="lp-field">
              <label htmlFor="lp-password">Пароль</label>
              <div className="lp-input-wrap">
                <svg className="lp-input-icon" viewBox="0 0 20 20" fill="currentColor">
                  <path fillRule="evenodd" d="M5 9V7a5 5 0 0110 0v2a2 2 0 012 2v5a2 2 0 01-2 2H5a2 2 0 01-2-2v-5a2 2 0 012-2zm8-2v2H7V7a3 3 0 016 0z" clipRule="evenodd"/>
                </svg>
                <input
                  id="lp-password"
                  name="password"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                />
              </div>
            </div>

            <button type="submit" className="lp-submit" disabled={loading}>
              {loading ? (
                <>
                  <span className="lp-spinner" />
                  Перевірка...
                </>
              ) : (
                'Увійти'
              )}
            </button>
          </form>
        </div>
      </div>
    </div>
  )
}
