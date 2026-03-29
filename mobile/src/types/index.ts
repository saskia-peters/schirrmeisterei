export type TicketStatus = 'new' | 'working' | 'waiting' | 'resolved' | 'closed'

export interface TicketSummary {
  id: string
  title: string
  status: TicketStatus
  creator_id: string
  owner_id: string | null
  created_at: string
  updated_at: string
}

export interface Ticket extends TicketSummary {
  description: string
  attachments: Attachment[]
  comments: Comment[]
  status_logs: StatusLog[]
}

export interface Attachment {
  id: string
  ticket_id: string
  filename: string
  content_type: string
  file_size: number
  uploaded_by_id: string
  created_at: string
}

export interface Comment {
  id: string
  ticket_id: string
  author_id: string
  content: string
  created_at: string
  updated_at: string
}

export interface StatusLog {
  id: string
  ticket_id: string
  changed_by: string
  from_status: TicketStatus | null
  to_status: TicketStatus
  note: string | null
  changed_at: string
}

export interface KanbanBoard {
  new: TicketSummary[]
  working: TicketSummary[]
  waiting: TicketSummary[]
  resolved: TicketSummary[]
  closed: TicketSummary[]
}
