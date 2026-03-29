import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { TicketCard } from '@/components/board/TicketCard'
import type { TicketSummary } from '@/types'

const mockTicket: TicketSummary = {
  id: 'ticket-1',
  title: 'Fix login bug',
  status: 'new',
  creator_id: 'user-1',
  creator_name: 'Alice',
  assignee_id: null,
  assignee_name: null,
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

describe('TicketCard', () => {
  it('renders ticket title', () => {
    render(<TicketCard ticket={mockTicket} onClick={() => {}} />)
    expect(screen.getByText('Fix login bug')).toBeInTheDocument()
  })

  it('calls onClick when clicked', async () => {
    const onClick = vi.fn()
    const { container } = render(<TicketCard ticket={mockTicket} onClick={onClick} />)
    const card = container.querySelector('.ticket-card')!
    card.dispatchEvent(new MouseEvent('click', { bubbles: true }))
    expect(onClick).toHaveBeenCalledTimes(1)
  })

  it('applies dragging class when isDragging is true', () => {
    const { container } = render(
      <TicketCard ticket={mockTicket} onClick={() => {}} isDragging />
    )
    expect(container.querySelector('.ticket-card--dragging')).toBeInTheDocument()
  })

  it('shows assigned indicator when assignee is set', () => {
    const ticket = { ...mockTicket, assignee_id: 'user-2', assignee_name: 'Bob' }
    const { container } = render(<TicketCard ticket={ticket} onClick={() => {}} />)
    expect(container.querySelector('.ticket-card-assigned')).toBeInTheDocument()
  })
})
