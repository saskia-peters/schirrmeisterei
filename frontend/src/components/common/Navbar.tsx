import { useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { authApi } from '@/api'
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
  const queryClient = useQueryClient()
  const isAdmin = user?.is_superuser || user?.groups?.includes('admin')

  const handleLogout = () => {
    // Fire-and-forget: revoke refresh tokens on the server + clear the cookie.
    // Even if the request fails, clear local state so the user is logged out.
    authApi.logout().catch(() => undefined)
    logout()
    queryClient.clear()
  }
  const navbarBg = user?.organization_level ? ORG_LEVEL_COLORS[user.organization_level] : undefined

  return (
    <nav className="navbar" style={navbarBg ? { backgroundColor: navbarBg } : undefined}>
      <div className="navbar-brand" style={{ cursor: 'pointer' }} onClick={() => navigate('/')}>
        <span className="navbar-logo">🎫</span>
        <span className="navbar-title">TicketSystem</span>
      </div>
      <div className="navbar-center">
        {user?.organization_name && <span className="navbar-org-name">{user.organization_name}</span>}
      </div>
      <div className="navbar-user">
        {user?.avatar_url ? (
          <img
            src={user.avatar_url}
            alt="Avatar"
            className="navbar-avatar"
            onClick={() => navigate('/profile')}
            title="My Profile"
          />
        ) : (
          <span style={{ cursor: 'pointer', fontSize: '0.875rem' }} onClick={() => navigate('/profile')}>
            {user?.full_name}
          </span>
        )}
        {isAdmin && (
          <button onClick={() => navigate('/admin')} className="btn btn-secondary btn-sm">⚙ Admin</button>
        )}
        <button onClick={() => navigate('/profile')} className="btn btn-ghost btn-sm">Profile</button>
        <button onClick={handleLogout} className="btn btn-ghost btn-sm">Sign Out</button>
      </div>
    </nav>
  )
}
