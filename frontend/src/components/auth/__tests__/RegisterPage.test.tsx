import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { RegisterPage } from '@/components/auth/RegisterPage'
import { authApi } from '@/api'
import type { Organization } from '@/types'

vi.mock('@/api', () => ({
  authApi: {
    register: vi.fn(),
    login: vi.fn(),
    me: vi.fn(),
  },
  adminApi: {},
}))

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

const mockSetTokens = vi.fn()
const mockSetUser = vi.fn()
vi.mock('@/store/authStore', () => ({
  useAuthStore: vi.fn(() => ({
    setTokens: mockSetTokens,
    setUser: mockSetUser,
  })),
}))

const mockLV: Organization = { id: 'lv-1', name: 'LV Bayern', level: 'landesverband', parent_id: null }
const mockRst: Organization = { id: 'rst-1', name: 'Rst München', level: 'regionalstelle', parent_id: 'lv-1' }
const mockOV: Organization = { id: 'ov-1', name: 'OV Schwabing', level: 'ortsverband', parent_id: 'rst-1' }

vi.mock('@/hooks/useApi', () => ({
  useLandesverbaende: vi.fn(() => ({ data: [mockLV] })),
  useRegionalstellen: vi.fn(() => ({ data: [mockRst] })),
  useOrtsverbaende: vi.fn(() => ({ data: [mockOV] })),
}))

describe('RegisterPage', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the registration form', () => {
    render(<RegisterPage onSwitchToLogin={() => {}} />)
    expect(screen.getByLabelText(/full name/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/email/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/^password$/i)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /create account/i })).toBeInTheDocument()
  })

  it('shows a validation error when email is invalid', async () => {
    render(<RegisterPage onSwitchToLogin={() => {}} />)
    await userEvent.type(screen.getByLabelText(/email/i), 'not-an-email')
    fireEvent.submit(screen.getByRole('button', { name: /create account/i }))
    await waitFor(() => {
      expect(screen.getByText(/invalid email/i)).toBeInTheDocument()
    })
  })

  it('shows validation error when passwords do not match', async () => {
    render(<RegisterPage onSwitchToLogin={() => {}} />)
    await userEvent.type(screen.getByLabelText(/^password$/i), 'Password1!')
    await userEvent.type(screen.getByLabelText(/confirm password/i), 'different')
    fireEvent.submit(screen.getByRole('button', { name: /create account/i }))
    await waitFor(() => {
      expect(screen.getByText(/passwords do not match/i)).toBeInTheDocument()
    })
  })

  it('calls register and login on valid submit', async () => {
    vi.mocked(authApi.register).mockResolvedValue(undefined as never)
    vi.mocked(authApi.login).mockResolvedValue({
      access_token: 'a',
      refresh_token: 'r',
      token_type: 'bearer',
    })
    vi.mocked(authApi.me).mockResolvedValue({
      id: '1',
      email: 'alice@example.com',
      full_name: 'Alice',
      is_active: true,
      is_superuser: false,
      force_password_change: false,
      groups: [],
      totp_enabled: false,
      organization_id: 'lv-1',
      organization_name: 'LV Bayern',
      organization_level: 'landesverband',
      org_abbrev: null,
      created_at: '',
      updated_at: '',
    })

    render(<RegisterPage onSwitchToLogin={() => {}} />)

    await userEvent.type(screen.getByLabelText(/full name/i), 'Alice')
    await userEvent.type(screen.getByLabelText(/email/i), 'alice@example.com')
    await userEvent.type(screen.getByLabelText(/^password$/i), 'Password1!')
    await userEvent.type(screen.getByLabelText(/confirm password/i), 'Password1!')

    // Select a Landesverband (required)
    await userEvent.selectOptions(screen.getByLabelText(/landesverband/i), 'lv-1')

    await userEvent.click(screen.getByRole('button', { name: /create account/i }))

    await waitFor(() => {
      expect(authApi.register).toHaveBeenCalled()
      expect(authApi.login).toHaveBeenCalled()
    })
  })

  it('calls onSwitchToLogin when the login link is clicked', async () => {
    const onSwitch = vi.fn()
    render(<RegisterPage onSwitchToLogin={onSwitch} />)
    await userEvent.click(screen.getByRole('button', { name: /sign in/i }))
    expect(onSwitch).toHaveBeenCalled()
  })
})
