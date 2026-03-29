import { useState } from 'react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { Toaster } from 'react-hot-toast'
import { useAuthStore } from '@/store/authStore'
import { LoginPage } from '@/components/auth/LoginPage'
import { RegisterPage } from '@/components/auth/RegisterPage'
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
      <Toaster position="top-right" />
    </QueryClientProvider>
  )
}

function AppInner() {
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated)
  const [view, setView] = useState<'login' | 'register'>('login')

  if (isAuthenticated) return <BoardPage />

  if (view === 'register') {
    return <RegisterPage onSwitchToLogin={() => setView('login')} />
  }

  return <LoginPage onSwitchToRegister={() => setView('register')} />
}
