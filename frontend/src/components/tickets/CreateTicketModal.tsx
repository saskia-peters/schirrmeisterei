import { useState, useRef } from 'react'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { toast } from 'sonner'
import { useCreateTicket, useAssignableUsers, useConfigItems } from '@/hooks/useApi'
import { ticketsApi } from '@/api'

const schema = z.object({
  title: z.string().min(1, 'Title is required').max(255),
  description: z.string().min(1, 'Description is required'),
  assignee_id: z.string().optional(),
  priority_id: z.string().optional(),
  category_id: z.string().optional(),
  affected_group_id: z.string().optional(),
})

type FormData = z.infer<typeof schema>

interface CreateTicketModalProps {
  onClose: () => void
  onCreated: (id: string) => void
}

export function CreateTicketModal({ onClose, onCreated }: CreateTicketModalProps) {
  const createTicket = useCreateTicket()
  const { data: assignableUsers = [] } = useAssignableUsers()
  const { data: priorities = [] } = useConfigItems('priority')
  const { data: categories = [] } = useConfigItems('category')
  const { data: groups = [] } = useConfigItems('group')

  const [pendingFiles, setPendingFiles] = useState<File[]>([])
  const [isUploading, setIsUploading] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema) })

  const onFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files ?? [])
    setPendingFiles((prev) => {
      const existing = new Set(prev.map((f) => `${f.name}-${f.size}`))
      return [...prev, ...files.filter((f) => !existing.has(`${f.name}-${f.size}`))]
    })
    if (fileInputRef.current) fileInputRef.current.value = ''
  }

  const removeFile = (index: number) => {
    setPendingFiles((prev) => prev.filter((_, i) => i !== index))
  }

  const onSubmit = async (data: FormData) => {
    try {
      setIsUploading(pendingFiles.length > 0)
      const ticket = await createTicket.mutateAsync({
        title: data.title,
        description: data.description,
        assignee_id: data.assignee_id || undefined,
        priority_id: data.priority_id || undefined,
        category_id: data.category_id || undefined,
        affected_group_id: data.affected_group_id || undefined,
      })
      for (const file of pendingFiles) {
        await ticketsApi.uploadAttachment(ticket.id, file)
      }
      toast.success('Ticket created!')
      onCreated(ticket.id)
    } catch {
      toast.error('Failed to create ticket')
    } finally {
      setIsUploading(false)
    }
  }

  const isBusy = createTicket.isPending || isUploading

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal" role="dialog" aria-modal aria-label="New Ticket">
        <div className="modal-header">
          <h2>New Ticket</h2>
          <button className="modal-close" onClick={onClose} aria-label="Close">✕</button>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="ticket-form">
          {/* Mandatory fields — always visible */}
          <div className="form-group">
            <label htmlFor="title">Title</label>
            <input id="title" type="text" {...register('title')} placeholder="Ticket title" autoFocus />
            {errors.title && <span className="error">{errors.title.message}</span>}
          </div>

          <div className="form-group">
            <label htmlFor="description">Description</label>
            <textarea
              id="description"
              {...register('description')}
              placeholder="Describe the issue…"
              rows={6}
            />
            {errors.description && <span className="error">{errors.description.message}</span>}
          </div>

          {/* File attachments — always visible, accepts images and PDFs */}
          <div className="form-group">
            <label>
              Attachments <span className="form-hint">(optional — images or PDFs)</span>
            </label>
            <label className="file-upload-label upload-btn">
              <span>📎 Choose files…</span>
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept="image/*,application/pdf"
                onChange={onFileChange}
                className="file-upload-input"
                aria-label="Attach files"
              />
            </label>
            {pendingFiles.length > 0 && (
              <ul className="file-list">
                {pendingFiles.map((f, i) => (
                  <li key={i} className="file-list-item">
                    <span className="file-list-name">{f.name}</span>
                    <span className="file-list-size">({Math.round(f.size / 1024)} KB)</span>
                    <button
                      type="button"
                      className="file-list-remove"
                      onClick={() => removeFile(i)}
                      aria-label={`Remove ${f.name}`}
                    >
                      ✕
                    </button>
                  </li>
                ))}
              </ul>
            )}
          </div>

          {/* Optional classification fields — hidden on mobile */}
          <div className="form-optional-fields">
            <div className="form-row">
              <div className="form-group">
                <label htmlFor="priority_id">Priority</label>
                <select id="priority_id" {...register('priority_id')}>
                  <option value="">— none —</option>
                  {priorities.map((p) => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="category_id">Category</label>
                <select id="category_id" {...register('category_id')}>
                  <option value="">— none —</option>
                  {categories.map((c) => (
                    <option key={c.id} value={c.id}>{c.name}</option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label htmlFor="affected_group_id">Affected Group</label>
                <select id="affected_group_id" {...register('affected_group_id')}>
                  <option value="">— none —</option>
                  {groups.map((g) => (
                    <option key={g.id} value={g.id}>{g.name}</option>
                  ))}
                </select>
              </div>
            </div>

            <div className="form-group">
              <label htmlFor="assignee_id">Assignee</label>
              <select id="assignee_id" {...register('assignee_id')}>
                <option value="">Unassigned</option>
                {assignableUsers.map((u) => (
                  <option key={u.id} value={u.id}>{u.full_name}</option>
                ))}
              </select>
            </div>
          </div>

          <div className="form-actions">
            <button type="button" onClick={onClose} className="btn btn-secondary">Cancel</button>
            <button type="submit" disabled={isBusy} className="btn btn-primary">
              {isUploading ? 'Uploading…' : isBusy ? 'Creating…' : 'Create Ticket'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
