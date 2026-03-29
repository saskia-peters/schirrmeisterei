import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { adminApi, authApi, ticketsApi, usersApi } from '@/api'
import type {
  CreateUserGroupRequest,
  ConfigItemType,
  CreateCommentRequest,
  CreateConfigItemRequest,
  CreateTicketRequest,
  UpdateConfigItemRequest,
  UpdateTicketRequest,
  UpdateTicketStatusRequest,
  UpdateUserGroupsRequest,
  UpdateUserGroupRequest,
} from '@/types'

// ─── Auth Hooks ───────────────────────────────────────────────────────────────

export const useCurrentUser = () =>
  useQuery({
    queryKey: ['me'],
    queryFn: authApi.me,
    retry: false,
  })

// ─── Ticket Hooks ─────────────────────────────────────────────────────────────

export const useKanbanBoard = () =>
  useQuery({
    queryKey: ['kanban'],
    queryFn: ticketsApi.getBoard,
    refetchInterval: 30_000,
  })

export const useTicket = (id: string) =>
  useQuery({
    queryKey: ['ticket', id],
    queryFn: () => ticketsApi.get(id),
    enabled: !!id,
  })

export const useCreateTicket = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: CreateTicketRequest) => ticketsApi.create(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['kanban'] }),
  })
}

export const useUpdateTicket = (id: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: UpdateTicketRequest) => ticketsApi.update(id, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ticket', id] })
      qc.invalidateQueries({ queryKey: ['kanban'] })
    },
  })
}

export const useUpdateTicketStatus = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateTicketStatusRequest }) =>
      ticketsApi.updateStatus(id, data),
    onSuccess: (_data, variables) => {
      qc.invalidateQueries({ queryKey: ['ticket', variables.id] })
      qc.invalidateQueries({ queryKey: ['kanban'] })
    },
  })
}

export const useDeleteTicket = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => ticketsApi.delete(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['kanban'] }),
  })
}

export const useAddComment = (ticketId: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: CreateCommentRequest) => ticketsApi.addComment(ticketId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ticket', ticketId] }),
  })
}

export const useDeleteComment = (ticketId: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (commentId: string) => ticketsApi.deleteComment(ticketId, commentId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ticket', ticketId] }),
  })
}

export const useUploadAttachment = (ticketId: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (file: File) => ticketsApi.uploadAttachment(ticketId, file),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ticket', ticketId] }),
  })
}

export const useDeleteAttachment = (ticketId: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (attachmentId: string) => ticketsApi.deleteAttachment(ticketId, attachmentId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ticket', ticketId] }),
  })
}

// ─── User Hooks ───────────────────────────────────────────────────────────────

export const useUsers = (enabled = true) =>
  useQuery({
    queryKey: ['users'],
    queryFn: usersApi.list,
    enabled,
  })

export const useAssignableUsers = () =>
  useQuery({
    queryKey: ['assignable-users'],
    queryFn: usersApi.assignable,
    staleTime: 60_000,
  })

// ─── Admin / Config Hooks ─────────────────────────────────────────────────────

export const useConfigItems = (type?: ConfigItemType, includeInactive = false) =>
  useQuery({
    queryKey: ['config-items', type, includeInactive],
    queryFn: () => adminApi.listConfigItems(type, includeInactive),
    staleTime: 60_000,
  })

export const useCreateConfigItem = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: CreateConfigItemRequest) => adminApi.createConfigItem(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['config-items'] }),
  })
}

export const useUpdateConfigItem = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateConfigItemRequest }) =>
      adminApi.updateConfigItem(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['config-items'] }),
  })
}

export const useDeleteConfigItem = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => adminApi.deleteConfigItem(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['config-items'] }),
  })
}

export const useUserGroups = (enabled = true) =>
  useQuery({
    queryKey: ['user-groups'],
    queryFn: adminApi.listUserGroups,
    staleTime: 60_000,
    enabled,
  })

export const useCreateUserGroup = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: CreateUserGroupRequest) => adminApi.createUserGroup(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['user-groups'] }),
  })
}

export const useUpdateUserGroup = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateUserGroupRequest }) =>
      adminApi.updateUserGroup(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['user-groups'] }),
  })
}

export const useDeleteUserGroup = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => adminApi.deleteUserGroup(id),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['user-groups'] }),
  })
}

export const useSetUserGroups = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ userId, data }: { userId: string; data: UpdateUserGroupsRequest }) =>
      adminApi.setUserGroups(userId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['users'] })
      qc.invalidateQueries({ queryKey: ['me'] })
    },
  })
}
