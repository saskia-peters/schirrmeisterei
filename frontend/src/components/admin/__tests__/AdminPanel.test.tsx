import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { AdminPanel } from '@/components/admin/AdminPanel'

vi.mock('react-router-dom', () => ({
  useNavigate: () => vi.fn(),
}))

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn(), warning: vi.fn() },
}))

vi.mock('@/store/authStore', () => ({
  useAuthStore: vi.fn(() => ({
    user: {
      id: 'user-1',
      is_superuser: true,
      groups: ['admin'],
      organization_level: 'leitung',
    },
  })),
}))

vi.mock('@/hooks/useApi', () => ({
  useUsers: vi.fn(() => ({ data: [] })),
  useConfigItems: vi.fn(() => ({ data: [], isLoading: false })),
  useCreateConfigItem: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  useUpdateConfigItem: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  useDeleteConfigItem: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  useUserGroups: vi.fn(() => ({ data: [] })),
  useCreateUserGroup: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  useUpdateUserGroup: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  useDeleteUserGroup: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  useSetUserGroups: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  useAppSettings: vi.fn(() => ({ data: [] })),
  useUpdateAppSetting: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  useAdminUsers: vi.fn(() => ({ data: [] })),
  useEmailConfigs: vi.fn(() => ({ data: [] })),
  useCreateEmailConfig: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  useUpdateEmailConfig: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  useOrganizations: vi.fn(() => ({ data: [] })),
  useBulkUploadUsers: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  useUploadHierarchy: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
  usePermissions: vi.fn(() => ({ data: [], isLoading: false })),
  useUserGroupsDetail: vi.fn(() => ({ data: [], isLoading: false })),
  useSetGroupPermissions: vi.fn(() => ({ mutateAsync: vi.fn(), isPending: false })),
}))

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

describe('AdminPanel', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the Administration heading', () => {
    render(<AdminPanel />, { wrapper })
    expect(screen.getByText('Administration')).toBeInTheDocument()
  })

  it('renders base tabs', () => {
    render(<AdminPanel />, { wrapper })
    expect(screen.getByRole('button', { name: 'Priorities' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Categories' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'User Roles' })).toBeInTheDocument()
  })

  it('renders admin-only tabs for admin user', () => {
    render(<AdminPanel />, { wrapper })
    expect(screen.getByRole('button', { name: 'Users' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Bulk Upload' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Hierarchy Import' })).toBeInTheDocument()
  })

  it('switches to Bulk Upload tab and shows upload UI', async () => {
    render(<AdminPanel />, { wrapper })
    await userEvent.click(screen.getByRole('button', { name: 'Bulk Upload' }))
    await waitFor(() => {
      expect(screen.getByText(/bulk user upload/i)).toBeInTheDocument()
    })
  })

  it('switches to Hierarchy Import tab and shows upload UI', async () => {
    render(<AdminPanel />, { wrapper })
    await userEvent.click(screen.getByRole('button', { name: 'Hierarchy Import' }))
    await waitFor(() => {
      expect(screen.getByText(/import organisation hierarchy/i)).toBeInTheDocument()
    })
  })

  it('switches to Role Permissions tab', async () => {
    render(<AdminPanel />, { wrapper })
    await userEvent.click(screen.getByRole('button', { name: 'Role Permissions' }))
    await waitFor(() => {
      expect(screen.getByText(/select role/i)).toBeInTheDocument()
    })
  })
})
