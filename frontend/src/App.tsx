import { useState, useEffect } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { Toaster } from 'sonner'
import { useAuthStore } from '@/store/authStore'
import { authApi } from '@/api'
import { LoginPage } from '@/components/auth/LoginPage'
import { RegisterPage } from '@/components/auth/RegisterPage'
import { ForcePasswordChangeModal } from '@/components/auth/ForcePasswordChangeModal'
import { ProfilePage } from '@/components/auth/ProfilePage'
import { BoardPage } from '@/components/board/BoardPage'
import { AdminPanel } from '@/components/admin/AdminPanel'
import '@/styles/globals.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 30_000 },
  },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <AppInner />
      </BrowserRouter>
      <Toaster position="top-right" richColors />
    </QueryClientProvider>
  )
}

function AppInner() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const user = useAuthStore((s) => s.user)
  const setUser = useAuthStore((s) => s.setUser)
  const logout = useAuthStore((s) => s.logout)
  const [view, setView] = useState<'login' | 'register'>('login')

  // Re-hydrate user after a page reload (user is not persisted in localStorage).
  useEffect(() => {
    if (isAuthenticated && !user) {
      authApi.me().then(setUser).catch(() => logout())
    }
  }, [isAuthenticated, user, setUser, logout])

  if (isAuthenticated) {
    if (user?.force_password_change) {
      return <ForcePasswordChangeModal />
    }
    return (
      <Routes>
        <Route path="/admin" element={<AdminPage />} />
        <Route path="/profile" element={<ProfilePage />} />
        <Route path="/" element={<BoardPage />} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    )
  }

  if (view === 'register') {
    return <RegisterPage onSwitchToLogin={() => setView('login')} />
  }

  return <LoginPage onSwitchToRegister={() => setView('register')} />
}

function AdminPage() {
  const { user } = useAuthStore()
  const isAdmin = user?.is_superuser || user?.groups?.includes('admin')
  if (!isAdmin) return <Navigate to="/" replace />
  return (
    <div className="app-layout">
      <AdminPanel />
    </div>
  )
}
