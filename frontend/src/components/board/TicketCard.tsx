import { formatDistanceToNow } from 'date-fns'
import type { TicketSummary } from '@/types'

const PRIORITY_CLASS: Record<string, string> = {
  Kritisch: 'priority-critical',
  Hoch: 'priority-high',
  Mittel: 'priority-medium',
  Gering: 'priority-low',
}

interface TicketCardProps {
  ticket: TicketSummary
  onClick: () => void
  isDragging?: boolean
}

export function TicketCard({ ticket, onClick, isDragging = false }: TicketCardProps) {
  return (
    <div
      className={`ticket-card ${isDragging ? 'ticket-card--dragging' : ''}`}
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => e.key === 'Enter' && onClick()}
      aria-label={`Ticket: ${ticket.title}`}
    >
      {ticket.priority_name && (
        <span className={`priority-badge ${PRIORITY_CLASS[ticket.priority_name] ?? 'priority-default'}`}>
          {ticket.priority_name}
        </span>
      )}
      <p className="ticket-card-title">{ticket.title}</p>
      {ticket.status === 'waiting' && ticket.waiting_for && (
        <p className="ticket-card-waiting-for" title={ticket.waiting_for}>
          Waiting for: {ticket.waiting_for}
        </p>
      )}
      <div className="ticket-card-meta">
        {ticket.category_name && (
          <span className="ticket-card-category">{ticket.category_name}</span>
        )}
        {ticket.affected_group_name && (
          <span className="ticket-card-group" title="Affected group">🏷 {ticket.affected_group_name}</span>
        )}
        <span className="ticket-card-date">
          {formatDistanceToNow(new Date(ticket.created_at), { addSuffix: true })}
        </span>
        {ticket.assignee_name
          ? <span className="ticket-card-assigned" title={`Assigned to ${ticket.assignee_name}`}>👤 {ticket.assignee_name}</span>
          : null}
      </div>
    </div>
  )
}
