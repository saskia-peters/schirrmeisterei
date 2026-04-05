import { useState, useEffect } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'sonner'
import { useAuthStore } from '@/store/authStore'
import { authApi } from '@/api'
import { LoginPage } from '@/components/auth/LoginPage'
import { RegisterPage } from '@/components/auth/RegisterPage'
import { ForcePasswordChangeModal } from '@/components/auth/ForcePasswordChangeModal'
import { BoardPage } from '@/components/board/BoardPage'
import '@/styles/globals.css'

const queryClient = new QueryClient({
  defaultOptions: {
    queries: { retry: 1, staleTime: 30_000 },
  },
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AppInner />
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
    return <BoardPage />
  }

  if (view === 'register') {
    return <RegisterPage onSwitchToLogin={() => setView('login')} />
  }

  return <LoginPage onSwitchToRegister={() => setView('register')} />
}
