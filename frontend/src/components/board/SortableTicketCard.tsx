import { useSortable } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import type { TicketSummary } from '@/types'
import { TicketCard } from './TicketCard'

interface SortableTicketCardProps {
  ticket: TicketSummary
  onTicketClick: (id: string) => void
}

export function SortableTicketCard({ ticket, onTicketClick }: SortableTicketCardProps) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({
    id: ticket.id,
  })

  const style: React.CSSProperties = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.3 : 1,
  }

  return (
    <div ref={setNodeRef} style={style} {...attributes} {...listeners}>
      <TicketCard ticket={ticket} onClick={() => onTicketClick(ticket.id)} />
    </div>
  )
}
