import { useState } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { formatDistanceToNow } from 'date-fns'
import { toast } from 'sonner'
import {
  useTicket,
  useUpdateTicket,
  useUpdateTicketStatus,
  useDeleteTicket,
  useAddComment,
  useDeleteComment,
  useUploadAttachment,
  useDeleteAttachment,
  useAssignableUsers,
  useConfigItems,
} from '@/hooks/useApi'
import { useAuthStore } from '@/store/authStore'
import type { TicketStatus } from '@/types'

const STATUS_OPTIONS: { value: TicketStatus; label: string }[] = [
  { value: 'new', label: 'New (ToDo)' },
  { value: 'working', label: 'Working' },
  { value: 'waiting', label: 'Waiting' },
  { value: 'resolved', label: 'Resolved' },
  { value: 'closed', label: 'Closed' },
]

const commentSchema = z.object({ content: z.string().min(1, 'Comment cannot be empty') })
type CommentForm = z.infer<typeof commentSchema>

interface TicketDetailProps {
  ticketId: string
  onClose: () => void
}

export function TicketDetail({ ticketId, onClose }: TicketDetailProps) {
  const { data: ticket, isLoading } = useTicket(ticketId)
  const { user } = useAuthStore()
  const { data: assignableUsers = [] } = useAssignableUsers()
  const { data: priorities = [] } = useConfigItems('priority')
  const { data: categories = [] } = useConfigItems('category')
  const { data: groups = [] } = useConfigItems('group')
  const [isEditing, setIsEditing] = useState(false)
  const [editTitle, setEditTitle] = useState('')
  const [editDescription, setEditDescription] = useState('')
  const [statusNote, setStatusNote] = useState('')

  const updateTicket = useUpdateTicket(ticketId)
  const updateStatus = useUpdateTicketStatus()
  const deleteTicket = useDeleteTicket()
  const addComment = useAddComment(ticketId)
  const deleteComment = useDeleteComment(ticketId)
  const uploadAttachment = useUploadAttachment(ticketId)
  const deleteAttachment = useDeleteAttachment(ticketId)

  const commentForm = useForm<CommentForm>({ resolver: zodResolver(commentSchema) })

  if (isLoading) return <div className="modal-overlay"><div className="modal">Loading…</div></div>
  if (!ticket) return null

  const latestWaitingReason = [...ticket.status_logs]
    .sort((a, b) => new Date(b.changed_at).getTime() - new Date(a.changed_at).getTime())
    .find((log) => log.to_status === 'waiting' && !!log.note?.trim())
    ?.note

  const canCloseTicket =
    user?.is_superuser ||
    user?.groups?.includes('schirrmeister') ||
    user?.groups?.includes('admin')

  const handleStartEdit = () => {
    setEditTitle(ticket.title)
    setEditDescription(ticket.description)
    setIsEditing(true)
  }

  const handleSaveEdit = async () => {
    try {
      await updateTicket.mutateAsync({ title: editTitle, description: editDescription })
      setIsEditing(false)
      toast.success('Ticket updated')
    } catch {
      toast.error('Failed to update ticket')
    }
  }

  const handleStatusChange = async (newStatus: TicketStatus) => {
    if (newStatus === 'waiting' && !statusNote.trim()) {
      toast.error('"Waiting for" note is required when status is Waiting')
      return
    }

    try {
      await updateStatus.mutateAsync({ id: ticketId, data: { status: newStatus, note: statusNote || undefined } })
      setStatusNote('')
      toast.success('Status updated')
    } catch {
      toast.error('Failed to update status')
    }
  }

  const handleDelete = async () => {
    if (!window.confirm('Delete this ticket?')) return
    try {
      await deleteTicket.mutateAsync(ticketId)
      toast.success('Ticket deleted')
      onClose()
    } catch {
      toast.error('Failed to delete ticket')
    }
  }

  const handleAddComment = async (data: CommentForm) => {
    try {
      await addComment.mutateAsync(data)
      commentForm.reset()
      toast.success('Comment added')
    } catch {
      toast.error('Failed to add comment')
    }
  }

  const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    try {
      await uploadAttachment.mutateAsync(file)
      toast.success('Attachment uploaded')
    } catch {
      toast.error('Failed to upload file')
    }
    e.target.value = ''
  }

  const handleDeleteAttachment = async (attachmentId: string) => {
    try {
      await deleteAttachment.mutateAsync(attachmentId)
      toast.success('Attachment removed')
    } catch {
      toast.error('Failed to remove attachment')
    }
  }

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal ticket-detail" role="dialog" aria-modal aria-label={ticket.title}>
        <div className="modal-header">
          {isEditing ? (
            <input
              value={editTitle}
              onChange={(e) => setEditTitle(e.target.value)}
              className="ticket-title-input"
            />
          ) : (
            <h2>{ticket.title}</h2>
          )}
          <button className="modal-close" onClick={onClose} aria-label="Close">✕</button>
        </div>

        <div className="ticket-meta">
          <span>Created {formatDistanceToNow(new Date(ticket.created_at), { addSuffix: true })}</span>
          <span>Updated {formatDistanceToNow(new Date(ticket.updated_at), { addSuffix: true })}</span>
        </div>

        {/* Status */}
        <div className="ticket-section">
          <h3>Status</h3>
          <div className="status-row">
            <select
              value={ticket.status}
              onChange={(e) => handleStatusChange(e.target.value as TicketStatus)}
              className="status-select"
            >
              {STATUS_OPTIONS.filter((s) => canCloseTicket || s.value !== 'closed').map((s) => (
                <option key={s.value} value={s.value}>{s.label}</option>
              ))}
            </select>
            <input
              type="text"
              placeholder='Waiting for... (required only when selecting "Waiting")'
              value={statusNote}
              onChange={(e) => setStatusNote(e.target.value)}
              className="status-note-input"
            />
          </div>
          {!canCloseTicket && (
            <p className="admin-loading">Only schirrmeister and admin can move tickets to closed.</p>
          )}
          {ticket.status === 'waiting' && latestWaitingReason && (
            <p className="waiting-for-display"><strong>Waiting for:</strong> {latestWaitingReason}</p>
          )}
        </div>

        {/* Assignee */}
        <div className="ticket-section">
          <h3>Assignee</h3>
          <select
            value={ticket.assignee_id ?? ''}
            onChange={(e) =>
              updateTicket.mutate({ assignee_id: e.target.value || null })
            }
            className="status-select"
          >
            <option value="">Unassigned</option>
            {assignableUsers.map((u) => (
              <option key={u.id} value={u.id}>{u.full_name}</option>
            ))}
          </select>
          {ticket.assignee_name && (
            <span className="assignee-badge">👤 {ticket.assignee_name}</span>
          )}
        </div>

        {/* Priority / Category / Affected Group */}
        <div className="ticket-section">
          <h3>Classification</h3>
          <div className="classification-row">
            <div className="form-group">
              <label>Priority</label>
              <select
                value={ticket.priority_id ?? ''}
                onChange={(e) => updateTicket.mutate({ priority_id: e.target.value || null })}
                className="status-select"
              >
                <option value="">— none —</option>
                {priorities.map((p) => (
                  <option key={p.id} value={p.id}>{p.name}</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label>Category</label>
              <select
                value={ticket.category_id ?? ''}
                onChange={(e) => updateTicket.mutate({ category_id: e.target.value || null })}
                className="status-select"
              >
                <option value="">— none —</option>
                {categories.map((c) => (
                  <option key={c.id} value={c.id}>{c.name}</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label>Affected Group</label>
              <select
                value={ticket.affected_group_id ?? ''}
                onChange={(e) => updateTicket.mutate({ affected_group_id: e.target.value || null })}
                className="status-select"
              >
                <option value="">— none —</option>
                {groups.map((g) => (
                  <option key={g.id} value={g.id}>{g.name}</option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Description */}
        <div className="ticket-section">
          <h3>Description</h3>
          {isEditing ? (
            <textarea
              value={editDescription}
              onChange={(e) => setEditDescription(e.target.value)}
              className="ticket-desc-input"
              rows={6}
            />
          ) : (
            <p className="ticket-description">{ticket.description}</p>
          )}
        </div>

        {/* Actions */}
        <div className="ticket-actions">
          {isEditing ? (
            <>
              <button onClick={handleSaveEdit} className="btn btn-primary">Save</button>
              <button onClick={() => setIsEditing(false)} className="btn btn-secondary">Cancel</button>
            </>
          ) : (
            <>
              <button onClick={handleStartEdit} className="btn btn-secondary">Edit</button>
              {(user?.id === ticket.creator_id || user?.is_superuser) && (
                <button onClick={handleDelete} className="btn btn-danger">Delete</button>
              )}
            </>
          )}
        </div>

        {/* Attachments */}
        <div className="ticket-section">
          <h3>Attachments ({ticket.attachments.length})</h3>
          <div className="attachments-grid">
            {ticket.attachments.map((att) => (
              <div key={att.id} className="attachment-thumbnail-wrap">
                <a
                  href={att.url}
                  target="_blank"
                  rel="noreferrer"
                  className="attachment-thumbnail"
                  title={`${att.filename} (${Math.round(att.file_size / 1024)} KB)`}
                >
                  <img src={att.url} alt={att.filename} className="thumbnail-img" />
                  <span className="thumbnail-name">{att.filename}</span>
                </a>
                {(user?.is_superuser || user?.id === att.uploaded_by_id) && (
                  <button
                    type="button"
                    className="attachment-delete-btn"
                    aria-label={`Remove ${att.filename}`}
                    title="Remove image"
                    onClick={() => handleDeleteAttachment(att.id)}
                  >
                    ✕
                  </button>
                )}
              </div>
            ))}
          </div>
          <label className="btn btn-secondary upload-btn">
            Upload Image
            <input
              type="file"
              accept="image/jpeg,image/png,image/gif,image/webp"
              onChange={handleFileUpload}
              hidden
            />
          </label>
        </div>

        {/* Comments */}
        <div className="ticket-section">
          <h3>Comments ({ticket.comments.length})</h3>
          <div className="comments-list">
            {ticket.comments.map((comment) => (
              <div key={comment.id} className="comment">
                <div className="comment-header">
                  <span className="comment-author">{comment.author_name}</span>
                  <span className="comment-date">
                    {formatDistanceToNow(new Date(comment.created_at), { addSuffix: true })}
                  </span>
                  {(user?.id === comment.author_id || user?.is_superuser) && (
                    <button
                      onClick={() => deleteComment.mutate(comment.id)}
                      className="comment-delete"
                      aria-label="Delete comment"
                    >
                      ✕
                    </button>
                  )}
                </div>
                <p>{comment.content}</p>
              </div>
            ))}
          </div>
          <form onSubmit={commentForm.handleSubmit(handleAddComment)} className="comment-form">
            <textarea
              {...commentForm.register('content')}
              placeholder="Add a comment…"
              rows={3}
            />
            {commentForm.formState.errors.content && (
              <span className="error">{commentForm.formState.errors.content.message}</span>
            )}
            <button type="submit" className="btn btn-primary">Add Comment</button>
          </form>
        </div>

        {/* Status Log */}
        <div className="ticket-section">
          <h3>Activity Log</h3>
          <div className="status-log">
            {[
              ...ticket.status_logs.map((log) => ({
                id: log.id,
                time: new Date(log.changed_at),
                render: () => {
                  const isAssigneeChange = log.note?.startsWith('Assignee changed:')
                  if (isAssigneeChange) {
                    return (
                      <>
                        <span className="log-icon">👤</span>
                        <span className="log-status">{log.note}</span>
                      </>
                    )
                  }
                  return (
                    <>
                      <span className="log-icon">🔄</span>
                      <span className="log-status">
                        {log.from_status && log.from_status !== log.to_status
                          ? `${log.from_status} → `
                          : ''}{log.to_status}
                      </span>
                      {log.note && !isAssigneeChange && <span className="log-note">: {log.note}</span>}
                    </>
                  )
                },
              })),
              ...ticket.comments.map((comment) => ({
                id: `comment-${comment.id}`,
                time: new Date(comment.created_at),
                render: () => (
                  <>
                    <span className="log-icon">💬</span>
                    <span className="log-status">Comment by {comment.author_name}</span>
                  </>
                ),
              })),
              ...ticket.attachments.map((att) => ({
                id: `att-${att.id}`,
                time: new Date(att.created_at),
                render: () => (
                  <>
                    <span className="log-icon">🖼</span>
                    <span className="log-status">Image uploaded: {att.filename}</span>
                  </>
                ),
              })),
            ]
              .sort((a, b) => a.time.getTime() - b.time.getTime())
              .map((entry) => (
                <div key={entry.id} className="status-log-entry">
                  {entry.render()}
                  <span className="log-date">
                    {formatDistanceToNow(entry.time, { addSuffix: true })}
                  </span>
                </div>
              ))}
          </div>
        </div>
      </div>
    </div>
  )
}
