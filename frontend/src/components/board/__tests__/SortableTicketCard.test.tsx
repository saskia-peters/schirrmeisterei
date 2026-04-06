import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { DndContext } from '@dnd-kit/core'
import { SortableContext } from '@dnd-kit/sortable'
import { SortableTicketCard } from '@/components/board/SortableTicketCard'
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
      <DndContext>
        <SortableContext items={['ticket-1']}>{children}</SortableContext>
      </DndContext>
    </QueryClientProvider>
  )
}

const mockTicket: TicketSummary = {
  id: 'ticket-1',
  title: 'Test ticket',
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
}

describe('SortableTicketCard', () => {
  it('renders the ticket title', () => {
    render(<SortableTicketCard ticket={mockTicket} onTicketClick={() => {}} />, { wrapper })
    expect(screen.getByText('Test ticket')).toBeInTheDocument()
  })

  it('calls onTicketClick with the ticket id when clicked', () => {
    const onClick = vi.fn()
    const { container } = render(
      <SortableTicketCard ticket={mockTicket} onTicketClick={onClick} />,
      { wrapper },
    )
    const card = container.querySelector('.ticket-card')!
    card.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    expect(onClick).toHaveBeenCalledWith('ticket-1')
  })
})
