import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { Navbar } from '@/components/common/Navbar'
import type { User } from '@/types'

const mockNavigate = vi.fn()
vi.mock('react-router-dom', () => ({
  useNavigate: () => mockNavigate,
}))

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

const mockLogout = vi.fn()
const mockUseAuthStore = vi.fn()

vi.mock('@/store/authStore', () => ({
  useAuthStore: () => mockUseAuthStore(),
}))

const baseUser: User = {
  id: 'user-1',
  email: 'alice@example.com',
  full_name: 'Alice',
  is_active: true,
  is_superuser: false,
  force_password_change: false,
  groups: ['helfende'],
  totp_enabled: false,
  avatar_url: null,
  organization_id: 'org-1',
  organization_name: 'OV München',
  organization_level: 'ortsverband',
  org_abbrev: null,
  created_at: '',
  updated_at: '',
}

describe('Navbar', () => {
  it('renders the user full name', () => {
    mockUseAuthStore.mockReturnValue({ user: baseUser, logout: mockLogout })
    render(<Navbar />)
    expect(screen.getByText(/Alice/)).toBeInTheDocument()
  })

  it('renders the organisation name in center', () => {
    mockUseAuthStore.mockReturnValue({ user: baseUser, logout: mockLogout })
    render(<Navbar />)
    expect(screen.getAllByText('OV München').length).toBeGreaterThan(0)
  })

  it('shows admin button for superuser', () => {
    mockUseAuthStore.mockReturnValue({
      user: { ...baseUser, is_superuser: true },
      logout: mockLogout,
    })
    render(<Navbar />)
    expect(screen.getByRole('button', { name: /admin/i })).toBeInTheDocument()
  })

  it('does not show admin button for regular user', () => {
    mockUseAuthStore.mockReturnValue({ user: baseUser, logout: mockLogout })
    render(<Navbar />)
    expect(screen.queryByRole('button', { name: /admin/i })).not.toBeInTheDocument()
  })

  it('applies light-blue background for ortsverband', () => {
    mockUseAuthStore.mockReturnValue({ user: baseUser, logout: mockLogout })
    const { container } = render(<Navbar />)
    const nav = container.querySelector('nav.navbar') as HTMLElement
    expect(nav.style.backgroundColor).toBe('rgb(219, 234, 254)')
  })

  it('applies light-orange background for regionalstelle', () => {
    mockUseAuthStore.mockReturnValue({
      user: { ...baseUser, organization_level: 'regionalstelle' },
      logout: mockLogout,
    })
    const { container } = render(<Navbar />)
    const nav = container.querySelector('nav.navbar') as HTMLElement
    expect(nav.style.backgroundColor).toBe('rgb(254, 215, 170)')
  })

  it('applies light-green background for landesverband', () => {
    mockUseAuthStore.mockReturnValue({
      user: { ...baseUser, organization_level: 'landesverband' },
      logout: mockLogout,
    })
    const { container } = render(<Navbar />)
    const nav = container.querySelector('nav.navbar') as HTMLElement
    expect(nav.style.backgroundColor).toBe('rgb(220, 252, 231)')
  })

  it('applies light-red background for leitung', () => {
    mockUseAuthStore.mockReturnValue({
      user: { ...baseUser, organization_level: 'leitung' },
      logout: mockLogout,
    })
    const { container } = render(<Navbar />)
    const nav = container.querySelector('nav.navbar') as HTMLElement
    expect(nav.style.backgroundColor).toBe('rgb(254, 226, 226)')
  })

  it('calls logout when Sign Out is clicked', async () => {
    const { default: userEvent } = await import('@testing-library/user-event')
    mockUseAuthStore.mockReturnValue({ user: baseUser, logout: mockLogout })
    render(<Navbar />)
    await userEvent.click(screen.getByRole('button', { name: /sign out/i }))
    expect(mockLogout).toHaveBeenCalled()
  })
})
