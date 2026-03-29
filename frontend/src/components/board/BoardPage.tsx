import { useState } from 'react'
import { KanbanBoard } from '@/components/board/KanbanBoard'
import { TicketDetail } from '@/components/tickets/TicketDetail'
import { CreateTicketModal } from '@/components/tickets/CreateTicketModal'
import { AdminPanel } from '@/components/admin/AdminPanel'
import { Navbar } from '@/components/common/Navbar'

export function BoardPage() {
  const [selectedTicketId, setSelectedTicketId] = useState<string | null>(null)
  const [showCreateModal, setShowCreateModal] = useState(false)
  const [showSettings, setShowSettings] = useState(false)

  return (
    <div className="app-layout">
      <Navbar onSettings={() => setShowSettings(true)} />

      <main className="app-main">
        <KanbanBoard
          onTicketClick={setSelectedTicketId}
          onNewTicket={() => setShowCreateModal(true)}
        />
      </main>

      {selectedTicketId && (
        <TicketDetail ticketId={selectedTicketId} onClose={() => setSelectedTicketId(null)} />
      )}

      {showCreateModal && (
        <CreateTicketModal
          onClose={() => setShowCreateModal(false)}
          onCreated={(id) => {
            setShowCreateModal(false)
            setSelectedTicketId(id)
          }}
        />
      )}

      {showSettings && (
        <AdminPanel onClose={() => setShowSettings(false)} />
      )}
    </div>
  )
}
