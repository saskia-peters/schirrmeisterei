import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import toast from 'react-hot-toast'
import { useCreateTicket, useAssignableUsers, useConfigItems } from '@/hooks/useApi'

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

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<FormData>({ resolver: zodResolver(schema) })

  const onSubmit = async (data: FormData) => {
    try {
      const ticket = await createTicket.mutateAsync({
        title: data.title,
        description: data.description,
        assignee_id: data.assignee_id || undefined,
        priority_id: data.priority_id || undefined,
        category_id: data.category_id || undefined,
        affected_group_id: data.affected_group_id || undefined,
      })
      toast.success('Ticket created!')
      onCreated(ticket.id)
    } catch {
      toast.error('Failed to create ticket')
    }
  }

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal" role="dialog" aria-modal aria-label="New Ticket">
        <div className="modal-header">
          <h2>New Ticket</h2>
          <button className="modal-close" onClick={onClose} aria-label="Close">✕</button>
        </div>

        <form onSubmit={handleSubmit(onSubmit)} className="ticket-form">
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

          <div className="form-actions">
            <button type="button" onClick={onClose} className="btn btn-secondary">Cancel</button>
            <button type="submit" disabled={createTicket.isPending} className="btn btn-primary">
              {createTicket.isPending ? 'Creating…' : 'Create Ticket'}
            </button>
          </div>
        </form>
      </div>
    </div>
  )
}
