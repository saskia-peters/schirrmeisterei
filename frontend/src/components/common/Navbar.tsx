import { useNavigate } from 'react-router-dom'
import { useAuthStore } from '@/store/authStore'

const ORG_LEVEL_COLORS: Record<string, string> = {
  ortsverband: '#dbeafe',
  regionalstelle: '#fed7aa',
  landesverband: '#dcfce7',
  leitung: '#fee2e2',
}

export function Navbar() {
  const { user, logout } = useAuthStore()
  const navigate = useNavigate()
  const isAdmin = user?.is_superuser || user?.groups?.includes('admin')
  const navbarBg = user?.organization_level ? ORG_LEVEL_COLORS[user.organization_level] : undefined

  return (
    <nav className="navbar" style={navbarBg ? { backgroundColor: navbarBg } : undefined}>
      <div className="navbar-brand">
        <span className="navbar-logo">🎫</span>
        <span className="navbar-title">TicketSystem</span>
      </div>
      <div className="navbar-center">
        {user?.organization_name && <span className="navbar-org-name">{user.organization_name}</span>}
      </div>
      <div className="navbar-user">
        <span>
          {user?.full_name}
          {user?.organization_name && <span className="org-badge"> ({user.organization_name})</span>}
        </span>
        {isAdmin && (
          <button onClick={() => navigate('/admin')} className="btn btn-secondary btn-sm">⚙ Admin</button>
        )}
        <button onClick={logout} className="btn btn-ghost btn-sm">Sign Out</button>
      </div>
    </nav>
  )
}
