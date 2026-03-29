import { View, Text, FlatList, TouchableOpacity, StyleSheet, RefreshControl } from 'react-native'
import { useQuery } from '@tanstack/react-query'
import { mobileTicketsApi } from '../api'
import type { KanbanBoard, TicketStatus, TicketSummary } from '../types'

const STATUS_LABELS: Record<TicketStatus, string> = {
  new: 'New',
  working: 'Working',
  waiting: 'Waiting',
  resolved: 'Resolved',
  closed: 'Closed',
}

const STATUS_COLORS: Record<TicketStatus, string> = {
  new: '#6366f1',
  working: '#f59e0b',
  waiting: '#8b5cf6',
  resolved: '#10b981',
  closed: '#6b7280',
}

interface TicketListScreenProps {
  onTicketPress: (id: string) => void
}

export function TicketListScreen({ onTicketPress }: TicketListScreenProps) {
  const { data: board, isLoading, refetch } = useQuery<KanbanBoard>({
    queryKey: ['kanban'],
    queryFn: mobileTicketsApi.getBoard,
  })

  const allTickets: TicketSummary[] = board
    ? [
        ...board.new,
        ...board.working,
        ...board.waiting,
        ...board.resolved,
        ...board.closed,
      ]
    : []

  return (
    <View style={styles.container}>
      <Text style={styles.header}>Tickets</Text>
      <FlatList
        data={allTickets}
        keyExtractor={(item) => item.id}
        refreshControl={<RefreshControl refreshing={isLoading} onRefresh={refetch} />}
        renderItem={({ item }) => (
          <TouchableOpacity
            style={styles.card}
            onPress={() => onTicketPress(item.id)}
            accessibilityLabel={`Ticket: ${item.title}`}
          >
            <View style={[styles.statusDot, { backgroundColor: STATUS_COLORS[item.status] }]} />
            <View style={styles.cardContent}>
              <Text style={styles.cardTitle}>{item.title}</Text>
              <Text style={styles.cardStatus}>{STATUS_LABELS[item.status]}</Text>
            </View>
          </TouchableOpacity>
        )}
        ListEmptyComponent={
          !isLoading ? <Text style={styles.empty}>No tickets yet</Text> : null
        }
      />
    </View>
  )
}

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f1f5f9', padding: 16 },
  header: { fontSize: 24, fontWeight: '700', marginBottom: 16 },
  card: {
    backgroundColor: '#fff',
    borderRadius: 8,
    padding: 12,
    marginBottom: 8,
    flexDirection: 'row',
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.08,
    shadowRadius: 2,
    elevation: 2,
  },
  statusDot: { width: 10, height: 10, borderRadius: 5, marginRight: 12 },
  cardContent: { flex: 1 },
  cardTitle: { fontSize: 15, fontWeight: '500' },
  cardStatus: { fontSize: 12, color: '#64748b', marginTop: 2 },
  empty: { textAlign: 'center', color: '#64748b', marginTop: 32 },
})
