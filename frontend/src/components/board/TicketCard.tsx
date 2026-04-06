import { differenceInDays, formatDistanceToNow } from 'date-fns'
import { useAppSettings } from '@/hooks/useApi'
import { useAuthStore } from '@/store/authStore'
import type { TicketSummary } from '@/types'

const PRIORITY_CLASS: Record<string, string> = {
  Kritisch: 'priority-critical',
  Hoch: 'priority-high',
  Mittel: 'priority-medium',
  Gering: 'priority-low',
}

const AGE_COLORS = [
  { cssVar: 'var(--age-dark-green)', label: 'dark-green' },
  { cssVar: 'var(--age-light-green)', label: 'light-green' },
  { cssVar: 'var(--age-yellow)', label: 'yellow' },
  { cssVar: 'var(--age-orange)', label: 'orange' },
  { cssVar: 'var(--age-light-red)', label: 'light-red' },
  { cssVar: 'var(--age-dark-red)', label: 'dark-red' },
]

function useAgeColor(daysOpen: number) {
  const { data: settings = [] } = useAppSettings()
  const get = (key: string, fallback: number) => {
    const s = settings.find((s) => s.key === key)
    return s ? parseInt(s.value, 10) || fallback : fallback
  }
  const thresholds = [
    get('age_green_days', 3),
    get('age_light_green_days', 7),
    get('age_yellow_days', 14),
    get('age_orange_days', 21),
    get('age_light_red_days', 30),
  ]
  const idx = thresholds.findIndex((t) => daysOpen <= t)
  return AGE_COLORS[idx === -1 ? 5 : idx].cssVar
}

interface TicketCardProps {
  ticket: TicketSummary
  onClick: () => void
  isDragging?: boolean
}

export function TicketCard({ ticket, onClick, isDragging = false }: TicketCardProps) {
  const daysOpen = differenceInDays(new Date(), new Date(ticket.created_at))
  const ageColor = useAgeColor(daysOpen)
  const { user } = useAuthStore()
  const showOrg = user?.organization_level && user.organization_level !== 'ortsverband'

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
      {showOrg && ticket.organization_name && (
        <span className="ticket-card-org" title="Organization">🏢 {ticket.organization_name}</span>
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
      <div
        className="ticket-age-bar"
        style={{ backgroundColor: ageColor }}
        title={`Open for ${daysOpen} day${daysOpen === 1 ? '' : 's'}`}
        aria-label={`Ticket age: ${daysOpen} days`}
      />
    </div>
  )
}
