import { useDroppable } from '@dnd-kit/core'
import { SortableContext, verticalListSortingStrategy } from '@dnd-kit/sortable'
import type { TicketStatus, TicketSummary } from '@/types'
import { SortableTicketCard } from './SortableTicketCard'

interface KanbanColumnProps {
  id: TicketStatus
  label: string
  color: string
  tickets: TicketSummary[]
  onTicketClick: (id: string) => void
}

export function KanbanColumn({ id, label, color, tickets, onTicketClick }: KanbanColumnProps) {
  const { setNodeRef, isOver } = useDroppable({ id })

  return (
    <div
      className={`kanban-column ${isOver ? 'kanban-column--over' : ''}`}
      style={{ '--column-color': color } as React.CSSProperties}
    >
      <div className="kanban-column-header">
        <span className="kanban-column-dot" />
        <h3>{label}</h3>
        <span className="kanban-column-count">{tickets.length}</span>
      </div>

      <div ref={setNodeRef} className="kanban-column-body">
        <SortableContext items={tickets.map((t) => t.id)} strategy={verticalListSortingStrategy}>
          {tickets.map((ticket) => (
            <SortableTicketCard key={ticket.id} ticket={ticket} onTicketClick={onTicketClick} />
          ))}
        </SortableContext>

        {tickets.length === 0 && (
          <div className="kanban-column-empty">Drop tickets here</div>
        )}
      </div>
    </div>
  )
}
