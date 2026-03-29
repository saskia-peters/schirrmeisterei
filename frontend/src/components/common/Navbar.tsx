import { useAuthStore } from '@/store/authStore'

interface NavbarProps {
  onSettings: () => void
}

export function Navbar({ onSettings }: NavbarProps) {
  const { user, logout } = useAuthStore()

  return (
    <nav className="navbar">
      <div className="navbar-brand">
        <span className="navbar-logo">🎫</span>
        <span className="navbar-title">TicketSystem</span>
      </div>
      <div className="navbar-user">
        <span>{user?.full_name}</span>
        <button onClick={onSettings} className="btn btn-secondary btn-sm">⚙ Settings</button>
        <button onClick={logout} className="btn btn-ghost btn-sm">Sign Out</button>
      </div>
    </nav>
  )
}
