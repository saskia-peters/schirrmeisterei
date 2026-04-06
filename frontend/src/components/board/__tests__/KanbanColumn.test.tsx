import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { DndContext } from '@dnd-kit/core'
import { KanbanColumn } from '@/components/board/KanbanColumn'
import type { TicketSummary } from '@/types'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'

vi.mock('@/store/authStore', () => ({
  useAuthStore: vi.fn(() => ({
    user: null,
  })),
}))

function wrapper({ children }: { children: React.ReactNode }) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return (
    <QueryClientProvider client={qc}>
      <DndContext>{children}</DndContext>
    </QueryClientProvider>
  )
}

const makeTicket = (id: string): TicketSummary => ({
  id,
  title: `Ticket ${id}`,
  status: 'new',
  creator_id: 'user-1',
  creator_name: 'Alice',
  assignee_id: null,
  assignee_name: null,
  organization_id: null,
  organization_name: null,
  priority_id: null,
  priority_name: null,
  category_id: null,
  category_name: null,
  affected_group_id: null,
  affected_group_name: null,
  waiting_for: null,
  created_at: new Date().toISOString(),
  updated_at: new Date().toISOString(),
})

describe('KanbanColumn', () => {
  it('renders the column label', () => {
    render(
      <KanbanColumn id="new" label="New" color="#2196f3" tickets={[]} onTicketClick={() => {}} />,
      { wrapper },
    )
    expect(screen.getByText('New')).toBeInTheDocument()
  })

  it('shows the ticket count', () => {
    const tickets = [makeTicket('t1'), makeTicket('t2')]
    render(
      <KanbanColumn id="new" label="New" color="#2196f3" tickets={tickets} onTicketClick={() => {}} />,
      { wrapper },
    )
    expect(screen.getByText('2')).toBeInTheDocument()
  })

  it('renders each ticket title', () => {
    const tickets = [makeTicket('t1'), makeTicket('t2')]
    render(
      <KanbanColumn id="new" label="New" color="#2196f3" tickets={tickets} onTicketClick={() => {}} />,
      { wrapper },
    )
    expect(screen.getByText('Ticket t1')).toBeInTheDocument()
    expect(screen.getByText('Ticket t2')).toBeInTheDocument()
  })

  it('shows empty placeholder when no tickets', () => {
    render(
      <KanbanColumn id="new" label="New" color="#2196f3" tickets={[]} onTicketClick={() => {}} />,
      { wrapper },
    )
    expect(screen.getByText(/drop tickets here/i)).toBeInTheDocument()
  })
})
