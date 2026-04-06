import { describe, it, expect, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { CreateTicketModal } from '@/components/tickets/CreateTicketModal'

vi.mock('sonner', () => ({
  toast: { success: vi.fn(), error: vi.fn() },
}))

const mockCreateTicketMutateAsync = vi.fn()

vi.mock('@/hooks/useApi', () => ({
  useCreateTicket: vi.fn(() => ({
    mutateAsync: mockCreateTicketMutateAsync,
    isPending: false,
  })),
  useAssignableUsers: vi.fn(() => ({ data: [] })),
  useConfigItems: vi.fn(() => ({ data: [] })),
}))

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return <QueryClientProvider client={qc}>{children}</QueryClientProvider>
}

describe('CreateTicketModal', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('renders the modal with title and description inputs', () => {
    render(<CreateTicketModal onClose={() => {}} onCreated={() => {}} />, { wrapper })
    expect(screen.getByRole('dialog')).toBeInTheDocument()
    expect(screen.getByLabelText(/title/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/description/i)).toBeInTheDocument()
  })

  it('shows validation errors when submitted empty', async () => {
    render(<CreateTicketModal onClose={() => {}} onCreated={() => {}} />, { wrapper })
    await userEvent.click(screen.getByRole('button', { name: /create ticket/i }))
    await waitFor(() => {
      expect(screen.getByText(/title is required/i)).toBeInTheDocument()
    })
  })

  it('calls onClose when Cancel is clicked', async () => {
    const onClose = vi.fn()
    render(<CreateTicketModal onClose={onClose} onCreated={() => {}} />, { wrapper })
    await userEvent.click(screen.getByRole('button', { name: /cancel/i }))
    expect(onClose).toHaveBeenCalled()
  })

  it('calls onClose when close button is clicked', async () => {
    const onClose = vi.fn()
    render(<CreateTicketModal onClose={onClose} onCreated={() => {}} />, { wrapper })
    await userEvent.click(screen.getByRole('button', { name: /close/i }))
    expect(onClose).toHaveBeenCalled()
  })

  it('submits and calls onCreated with the new ticket id', async () => {
    mockCreateTicketMutateAsync.mockResolvedValue({ id: 'new-ticket-id' })
    const onCreated = vi.fn()
    render(<CreateTicketModal onClose={() => {}} onCreated={onCreated} />, { wrapper })

    await userEvent.type(screen.getByLabelText(/title/i), 'My new ticket')
    await userEvent.type(screen.getByLabelText(/description/i), 'Some description')
    await userEvent.click(screen.getByRole('button', { name: /create ticket/i }))

    await waitFor(() => {
      expect(mockCreateTicketMutateAsync).toHaveBeenCalled()
      expect(onCreated).toHaveBeenCalledWith('new-ticket-id')
    })
  })
})
