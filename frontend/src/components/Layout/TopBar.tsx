import { useNavigate } from 'react-router-dom'
import useAppStore from '../../store/useAppStore'

export default function TopBar() {
  const navigate = useNavigate()
  const { clearToken, role } = useAppStore()
  const isAdmin = role === 'admin'

  const logout = () => {
    clearToken()
    navigate('/login', { replace: true })
  }

  return (
    <div className="topbar">
      <div className="topbar-logo">
        <svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
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
      <h1>Agro Monitoring</h1>
      {isAdmin && (
        <button className="topbar-logout" onClick={() => navigate('/users')}>
          Користувачі
        </button>
      )}
      <div className="topbar-role-badge">{role === 'admin' ? 'Адмін' : 'Співробітник'}</div>
      <button className="topbar-logout" onClick={logout}>Вийти</button>
    </div>
  )
}
