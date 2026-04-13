import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { LoginPage } from '@/components/auth/LoginPage'
import { authApi } from '@/api'

vi.mock('@/api', () => ({
  authApi: {
    login: vi.fn(),
    me: vi.fn(),
  },
}))

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn(), info: vi.fn() },
}))

const mockSetTokens = vi.fn()
const mockSetUser = vi.fn()

vi.mock('@/store/authStore', () => ({
  useAuthStore: vi.fn(() => ({
    setTokens: mockSetTokens,
    setUser: mockSetUser,
  })),
}))

describe('LoginPage', () => {
  const onSwitchToRegister = vi.fn()

  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders login form', () => {
    render(<LoginPage onSwitchToRegister={onSwitchToRegister} />)
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/password/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /sign in/i })).toBeInTheDocument()
  })

  it('shows validation error for invalid email', async () => {
    render(<LoginPage onSwitchToRegister={onSwitchToRegister} />)
    await userEvent.type(screen.getByLabelText(/email/i), 'not-an-email')
    fireEvent.submit(screen.getByRole('button', { name: /sign in/i }))
    await waitFor(() => {
      expect(screen.getByText(/invalid email/i)).toBeInTheDocument()
    })
  })

  it('calls login API on valid submit', async () => {
    vi.mocked(authApi.login).mockResolvedValue({
      access_token: 'access',
      token_type: 'bearer',
    })
    vi.mocked(authApi.me).mockResolvedValue({
      id: '1',
      email: 'test@example.com',
      full_name: 'Test',
      is_active: true,
      is_superuser: false,
      force_password_change: false,
      groups: ['helfende'],
      totp_enabled: false,
      avatar_url: null,
      organization_id: null,
      organization_name: null,
      organization_level: null,
      org_abbrev: null,
      created_at: '',
      updated_at: '',
    })

    render(<LoginPage onSwitchToRegister={onSwitchToRegister} />)
    await userEvent.type(screen.getByLabelText(/email/i), 'test@example.com')
    await userEvent.type(screen.getByLabelText(/password/i), 'password123')
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }))

    await waitFor(() => {
      expect(authApi.login).toHaveBeenCalledWith({
        email: 'test@example.com',
        password: 'password123',
        totp_code: undefined,
      })
    })
  })

  it('calls onSwitchToRegister when register link is clicked', async () => {
    render(<LoginPage onSwitchToRegister={onSwitchToRegister} />)
    await userEvent.click(screen.getByRole('button', { name: /register/i }))
    expect(onSwitchToRegister).toHaveBeenCalled()
  })
})
