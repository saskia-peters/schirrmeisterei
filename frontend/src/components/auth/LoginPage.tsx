import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import { authApi } from '@/api'
import { useAuthStore } from '@/store/authStore'

const loginSchema = z.object({
  email: z.string().email('Invalid email address'),
  password: z.string().min(1, 'Password is required'),
  totp_code: z.string().optional(),
})

type LoginForm = z.infer<typeof loginSchema>

interface LoginPageProps {
  onSwitchToRegister: () => void
}

export function LoginPage({ onSwitchToRegister }: LoginPageProps) {
  const [requireTotp, setRequireTotp] = useState(false)
  const [isLoading, setIsLoading] = useState(false)
  const { setTokens, setUser } = useAuthStore()

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginForm>({ resolver: zodResolver(loginSchema) })

  const onSubmit = async (data: LoginForm) => {
    setIsLoading(true)
    try {
      const tokens = await authApi.login(data)
      setTokens(tokens.access_token, tokens.refresh_token)
      const user = await authApi.me()
      setUser(user)
      toast.success('Logged in successfully')
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string }; status?: number } }
      if (error.response?.data?.detail === 'TOTP code required') {
        setRequireTotp(true)
        toast.info('🔐 Please enter your authenticator code')
      } else {
        toast.error(error.response?.data?.detail ?? 'Login failed')
      }
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1>TicketSystem</h1>
        <h2>Sign In</h2>
        <form onSubmit={handleSubmit(onSubmit)} className="auth-form">
          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input id="email" type="email" {...register('email')} placeholder="you@example.com" />
            {errors.email && <span className="error">{errors.email.message}</span>}
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input id="password" type="password" {...register('password')} placeholder="••••••••" />
            {errors.password && <span className="error">{errors.password.message}</span>}
          </div>

          {requireTotp && (
            <div className="form-group">
              <label htmlFor="totp_code">Authenticator Code</label>
              <input
                id="totp_code"
                type="text"
                maxLength={6}
                {...register('totp_code')}
                placeholder="000000"
                autoFocus
              />
            </div>
          )}

          <button type="submit" disabled={isLoading} className="btn btn-primary btn-full">
            {isLoading ? 'Signing in…' : 'Sign In'}
          </button>
        </form>

        <p className="auth-switch">
          Don&apos;t have an account?{' '}
          <button type="button" onClick={onSwitchToRegister} className="link-btn">
            Register
          </button>
        </p>
      </div>
    </div>
  )
}
