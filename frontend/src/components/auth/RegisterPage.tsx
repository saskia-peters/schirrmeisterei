import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import { authApi } from '@/api'
import { useAuthStore } from '@/store/authStore'
import { useLandesverbaende, useRegionalstellen, useOrtsverbaende } from '@/hooks/useApi'

const registerSchema = z.object({
  email: z.string().email('Invalid email address'),
  full_name: z.string().min(1, 'Full name is required'),
  password: z.string().min(8, 'Password must be at least 8 characters'),
  confirm_password: z.string(),
  landesverband_id: z.string().min(1, 'Please select a Landesverband'),
  regionalstelle_id: z.string().optional(),
  organization_id: z.string().optional(),
}).refine((d) => d.password === d.confirm_password, {
  message: 'Passwords do not match',
  path: ['confirm_password'],
})

type RegisterForm = z.infer<typeof registerSchema>

interface RegisterPageProps {
  onSwitchToLogin: () => void
}

export function RegisterPage({ onSwitchToLogin }: RegisterPageProps) {
  const [isLoading, setIsLoading] = useState(false)
  const { setTokens, setUser } = useAuthStore()

  const {
    register,
    handleSubmit,
    watch,
    setValue,
    formState: { errors },
  } = useForm<RegisterForm>({ resolver: zodResolver(registerSchema) })

  const selectedLV = watch('landesverband_id')
  const selectedRst = watch('regionalstelle_id')

  const { data: landesverbaende = [] } = useLandesverbaende()
  const { data: regionalstellen = [] } = useRegionalstellen(selectedLV)
  const { data: ortsverbaende = [] } = useOrtsverbaende(selectedRst)

  const onSubmit = async (data: RegisterForm) => {
    setIsLoading(true)
    try {
      const effectiveOrgId = data.organization_id || data.regionalstelle_id || data.landesverband_id
      await authApi.register({
        email: data.email,
        full_name: data.full_name,
        password: data.password,
        organization_id: effectiveOrgId,
      })
      const tokens = await authApi.login({ email: data.email, password: data.password })
      setTokens(tokens.access_token, tokens.refresh_token)
      const user = await authApi.me()
      setUser(user)
      toast.success('Account created successfully!')
    } catch (err: unknown) {
      const error = err as { response?: { data?: { detail?: string } } }
      toast.error(error.response?.data?.detail ?? 'Registration failed')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="auth-page">
      <div className="auth-card">
        <h1>TicketSystem</h1>
        <h2>Create Account</h2>
        <form onSubmit={handleSubmit(onSubmit)} className="auth-form">
          <div className="form-group">
            <label htmlFor="full_name">Full Name</label>
            <input id="full_name" type="text" {...register('full_name')} placeholder="Jane Doe" />
            {errors.full_name && <span className="error">{errors.full_name.message}</span>}
          </div>

          <div className="form-group">
            <label htmlFor="email">Email</label>
            <input id="email" type="email" {...register('email')} placeholder="you@example.com" />
            {errors.email && <span className="error">{errors.email.message}</span>}
          </div>

          <div className="form-group">
            <label htmlFor="landesverband_id">Landesverband</label>
            <select
              id="landesverband_id"
              {...register('landesverband_id')}
              onChange={(e) => {
                setValue('landesverband_id', e.target.value)
                setValue('regionalstelle_id', '')
                setValue('organization_id', '')
              }}
            >
              <option value="">-- Select Landesverband --</option>
              {landesverbaende.map((lv) => (
                <option key={lv.id} value={lv.id}>{lv.name}</option>
              ))}
            </select>
            {errors.landesverband_id && <span className="error">{errors.landesverband_id.message}</span>}
          </div>

          <div className="form-group">
            <label htmlFor="regionalstelle_id">Regionalstelle (optional)</label>
            <select
              id="regionalstelle_id"
              {...register('regionalstelle_id')}
              disabled={!selectedLV}
              onChange={(e) => {
                setValue('regionalstelle_id', e.target.value)
                setValue('organization_id', '')
              }}
            >
              <option value="">-- Select Regionalstelle --</option>
              {regionalstellen.map((rst) => (
                <option key={rst.id} value={rst.id}>{rst.name}</option>
              ))}
            </select>
            {errors.regionalstelle_id && <span className="error">{errors.regionalstelle_id.message}</span>}
          </div>

          <div className="form-group">
            <label htmlFor="organization_id">Ortsverband (optional)</label>
            <select
              id="organization_id"
              {...register('organization_id')}
              disabled={!selectedRst}
            >
              <option value="">-- Select Ortsverband --</option>
              {ortsverbaende.map((ov) => (
                <option key={ov.id} value={ov.id}>{ov.name}</option>
              ))}
            </select>
            {errors.organization_id && <span className="error">{errors.organization_id.message}</span>}
          </div>

          <div className="form-group">
            <label htmlFor="password">Password</label>
            <input id="password" type="password" {...register('password')} placeholder="min. 8 chars" />
            {errors.password && <span className="error">{errors.password.message}</span>}
          </div>

          <div className="form-group">
            <label htmlFor="confirm_password">Confirm Password</label>
            <input
              id="confirm_password"
              type="password"
              {...register('confirm_password')}
              placeholder="••••••••"
            />
            {errors.confirm_password && (
              <span className="error">{errors.confirm_password.message}</span>
            )}
          </div>

          <button type="submit" disabled={isLoading} className="btn btn-primary btn-full">
            {isLoading ? 'Creating account…' : 'Create Account'}
          </button>
        </form>

        <p className="auth-switch">
          Already have an account?{' '}
          <button type="button" onClick={onSwitchToLogin} className="link-btn">
            Sign In
          </button>
        </p>
      </div>
    </div>
  )
}
