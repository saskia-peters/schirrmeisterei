import {
  DndContext,
  DragEndEvent,
  DragOverlay,
  DragStartEvent,
  PointerSensor,
  useSensor,
  useSensors,
  closestCorners,
} from '@dnd-kit/core'
import { useState } from 'react'
import toast from 'react-hot-toast'
import { useKanbanBoard, useUpdateTicketStatus, useAssignableUsers, useConfigItems } from '@/hooks/useApi'
import type { TicketStatus, TicketSummary } from '@/types'
import { KanbanColumn } from './KanbanColumn'
import { TicketCard } from './TicketCard'

const COLUMNS: { id: TicketStatus; label: string; color: string }[] = [
  { id: 'new', label: 'New (ToDo)', color: '#6366f1' },
  { id: 'working', label: 'Working', color: '#f59e0b' },
  { id: 'waiting', label: 'Waiting', color: '#8b5cf6' },
  { id: 'resolved', label: 'Resolved', color: '#10b981' },
  { id: 'closed', label: 'Closed', color: '#6b7280' },
]

interface KanbanBoardProps {
  onTicketClick: (id: string) => void
  onNewTicket: () => void
}

export function KanbanBoard({ onTicketClick, onNewTicket }: KanbanBoardProps) {
  const { data: board, isLoading } = useKanbanBoard()
  const { data: assignableUsers = [] } = useAssignableUsers()
  const { data: priorities = [] } = useConfigItems('priority')
  const { data: categories = [] } = useConfigItems('category')
  const { data: groups = [] } = useConfigItems('group')
  const updateStatus = useUpdateTicketStatus()
  const [activeTicket, setActiveTicket] = useState<TicketSummary | null>(null)
  const [filterDate, setFilterDate] = useState('')
  const [filterCreator, setFilterCreator] = useState('')
  const [filterAssignee, setFilterAssignee] = useState('')
  const [filterPriority, setFilterPriority] = useState('')
  const [filterCategory, setFilterCategory] = useState('')
  const [filterGroup, setFilterGroup] = useState('')
  const [waitingTicket, setWaitingTicket] = useState<TicketSummary | null>(null)
  const [waitingNote, setWaitingNote] = useState('')

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } })
  )

  if (isLoading) {
    return <div className="board-loading">Loading board…</div>
  }

  if (!board) return null

  const allTickets = [
    ...board.new,
    ...board.working,
    ...board.waiting,
    ...board.resolved,
    ...board.closed,
  ]

  const uniqueCreators = [...new Set(allTickets.map((t) => t.creator_name).filter(Boolean))].sort()

  const applyFilters = (tickets: TicketSummary[]) =>
    tickets.filter((t) => {
      const dateOk = !filterDate || new Date(t.created_at) >= new Date(filterDate)
      const creatorOk = !filterCreator || t.creator_name === filterCreator
      const assigneeOk =
        !filterAssignee ||
        (filterAssignee === '__unassigned__'
          ? t.assignee_id == null
          : t.assignee_name === filterAssignee)
      const priorityOk = !filterPriority || t.priority_name === filterPriority
      const categoryOk = !filterCategory || t.category_name === filterCategory
      const groupOk = !filterGroup || t.affected_group_name === filterGroup
      return dateOk && creatorOk && assigneeOk && priorityOk && categoryOk && groupOk
    })

  const handleDragStart = (event: DragStartEvent) => {
    const ticket = allTickets.find((t) => t.id === event.active.id)
    setActiveTicket(ticket ?? null)
  }

  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event
    setActiveTicket(null)

    if (!over) return

    const ticketId = active.id as string
    const newStatus = over.id as TicketStatus

    const ticket = allTickets.find((t) => t.id === ticketId)
    if (!ticket || ticket.status === newStatus) return

    if (newStatus === 'waiting') {
      setWaitingTicket(ticket)
      setWaitingNote('')
      return
    }

    updateStatus.mutate(
      { id: ticketId, data: { status: newStatus } },
      {
        onError: () => toast.error('Failed to update ticket status'),
      }
    )
  }

  const handleConfirmWaiting = () => {
    if (!waitingTicket) return
    const note = waitingNote.trim()
    if (!note) {
      toast.error('Please provide "Waiting for" before moving to Waiting')
      return
    }

    updateStatus.mutate(
      { id: waitingTicket.id, data: { status: 'waiting', note } },
      {
        onSuccess: () => {
          setWaitingTicket(null)
          setWaitingNote('')
        },
        onError: () => toast.error('Failed to update ticket status'),
      }
    )
  }

  const handleCancelWaiting = () => {
    setWaitingTicket(null)
    setWaitingNote('')
  }

  return (
    <div className="board-container">
      <div className="board-header">
        <h1>Schirrmeisterei</h1>
        <button onClick={onNewTicket} className="btn btn-primary">
          + New Ticket
        </button>
      </div>

      <div className="board-filters">
        <label>
          Created after:
          <input
            type="date"
            value={filterDate}
            onChange={(e) => setFilterDate(e.target.value)}
          />
        </label>
        <label>
          Creator:
          <select value={filterCreator} onChange={(e) => setFilterCreator(e.target.value)}>
            <option value="">All users</option>
            {uniqueCreators.map((c) => (
              <option key={c} value={c}>{c}</option>
            ))}
          </select>
        </label>
        <label>
          Assignee:
          <select value={filterAssignee} onChange={(e) => setFilterAssignee(e.target.value)}>
            <option value="">All</option>
            <option value="__unassigned__">Unassigned</option>
            {assignableUsers.map((u) => (
              <option key={u.id} value={u.full_name}>{u.full_name}</option>
            ))}
          </select>
        </label>
        {priorities.length > 0 && (
          <label>
            Priority:
            <select value={filterPriority} onChange={(e) => setFilterPriority(e.target.value)}>
              <option value="">All</option>
              {priorities.map((p) => (
                <option key={p.id} value={p.name}>{p.name}</option>
              ))}
            </select>
          </label>
        )}
        {categories.length > 0 && (
          <label>
            Category:
            <select value={filterCategory} onChange={(e) => setFilterCategory(e.target.value)}>
              <option value="">All</option>
              {categories.map((c) => (
                <option key={c.id} value={c.name}>{c.name}</option>
              ))}
            </select>
          </label>
        )}
        {groups.length > 0 && (
          <label>
            Group:
            <select value={filterGroup} onChange={(e) => setFilterGroup(e.target.value)}>
              <option value="">All</option>
              {groups.map((g) => (
                <option key={g.id} value={g.name}>{g.name}</option>
              ))}
            </select>
          </label>
        )}
        {(filterDate || filterCreator || filterAssignee || filterPriority || filterCategory || filterGroup) && (
          <button
            onClick={() => { setFilterDate(''); setFilterCreator(''); setFilterAssignee(''); setFilterPriority(''); setFilterCategory(''); setFilterGroup('') }}
            className="btn btn-sm btn-ghost"
          >
            ✕ Clear filters
          </button>
        )}
      </div>

      <DndContext
        sensors={sensors}
        collisionDetection={closestCorners}
        onDragStart={handleDragStart}
        onDragEnd={handleDragEnd}
      >
        <div className="board-columns">
          {COLUMNS.map((col) => (
            <KanbanColumn
              key={col.id}
              id={col.id}
              label={col.label}
              color={col.color}
              tickets={applyFilters(board[col.id])}
              onTicketClick={onTicketClick}
            />
          ))}
        </div>

        <DragOverlay>
          {activeTicket && (
            <TicketCard ticket={activeTicket} onClick={() => {}} isDragging />
          )}
        </DragOverlay>
      </DndContext>

      {waitingTicket && (
        <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && handleCancelWaiting()}>
          <div className="modal waiting-note-modal" role="dialog" aria-modal aria-label="Waiting Reason">
            <div className="modal-header">
              <h2>Move To Waiting</h2>
              <button className="modal-close" onClick={handleCancelWaiting} aria-label="Close">✕</button>
            </div>
            <div className="ticket-form">
              <p className="admin-loading">Ticket: {waitingTicket.title}</p>
              <div className="form-group">
                <label htmlFor="waiting-note-input">Waiting for</label>
                <textarea
                  id="waiting-note-input"
                  rows={3}
                  value={waitingNote}
                  onChange={(e) => setWaitingNote(e.target.value)}
                  placeholder="Describe what this ticket is waiting for..."
                  autoFocus
                />
              </div>
              <div className="form-actions">
                <button type="button" className="btn btn-secondary" onClick={handleCancelWaiting}>Cancel</button>
                <button
                  type="button"
                  className="btn btn-primary"
                  onClick={handleConfirmWaiting}
                  disabled={updateStatus.isPending}
                >
                  {updateStatus.isPending ? 'Saving…' : 'Move To Waiting'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
