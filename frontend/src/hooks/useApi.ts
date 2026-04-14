import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { adminApi, authApi, organizationsApi, ticketsApi, usersApi } from '@/api'
import type {
  AdminUserCreateRequest,
  AdminUserUpdateRequest,
  CreateEmailConfigRequest,
  CreateUserGroupRequest,
  ConfigItemType,
  CreateCommentRequest,
  CreateConfigItemRequest,
  CreateTicketRequest,
  PasswordResetConfirm,
  PasswordResetRequest,
  UpdateConfigItemRequest,
  UpdateEmailConfigRequest,
  UpdateTicketRequest,
  UpdateTicketStatusRequest,
  UpdateUserGroupsRequest,
  UpdateUserGroupRequest,
  UpdateWaitingForRequest,
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

export const useUpdateWaitingFor = (ticketId: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: UpdateWaitingForRequest) => ticketsApi.updateWaitingFor(ticketId, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['ticket', ticketId] })
      qc.invalidateQueries({ queryKey: ['kanban'] })
    },
  })
}

export const useWatchTicket = (ticketId: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => ticketsApi.watchTicket(ticketId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['ticket', ticketId] }),
  })
}

export const useUnwatchTicket = (ticketId: string) => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => ticketsApi.unwatchTicket(ticketId),
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

export const useAppSettings = () =>
  useQuery({
    queryKey: ['app-settings'],
    queryFn: adminApi.getAppSettings,
    staleTime: 5 * 60_000,
  })

export const useUpdateAppSetting = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ key, value }: { key: string; value: string }) =>
      adminApi.updateAppSetting(key, { value }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['app-settings'] }),
  })
}

export const useAdminUsers = (
  filters?: { landesverband_id?: string; regionalstelle_id?: string; ortsverband_id?: string },
  enabled = true,
) =>
  useQuery({
    queryKey: ['admin-users', filters],
    queryFn: () => adminApi.listUsers(filters),
    enabled,
    staleTime: 30_000,
  })

export const useCreateAdminUser = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: AdminUserCreateRequest) => adminApi.createUser(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-users'] }),
  })
}

export const useUpdateAdminUser = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ userId, data }: { userId: string; data: AdminUserUpdateRequest }) =>
      adminApi.updateUser(userId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-users'] }),
  })
}

// ─── Organization Hooks ───────────────────────────────────────────────────────

export const useOrganizations = (params?: { level?: string; parent_id?: string }) =>
  useQuery({
    queryKey: ['organizations', params],
    queryFn: () => organizationsApi.list(params),
    staleTime: 5 * 60_000,
  })

export const useLandesverbaende = () =>
  useQuery({
    queryKey: ['organizations', 'landesverbaende'],
    queryFn: organizationsApi.listLandesverbaende,
    staleTime: 5 * 60_000,
  })

export const useRegionalstellen = (landesverbandId?: string) =>
  useQuery({
    queryKey: ['organizations', 'regionalstellen', landesverbandId],
    queryFn: () => organizationsApi.listRegionalstellen(landesverbandId),
    enabled: !!landesverbandId,
    staleTime: 5 * 60_000,
  })

export const useOrtsverbaende = (regionalstelleId?: string) =>
  useQuery({
    queryKey: ['organizations', 'ortsverbaende', regionalstelleId],
    queryFn: () => organizationsApi.listOrtsverbaende(regionalstelleId),
    enabled: !!regionalstelleId,
    staleTime: 5 * 60_000,
  })

// ─── Password Reset Hooks ─────────────────────────────────────────────────────

export const useRequestPasswordReset = () =>
  useMutation({
    mutationFn: (data: PasswordResetRequest) => authApi.requestPasswordReset(data),
  })

export const useConfirmPasswordReset = () =>
  useMutation({
    mutationFn: (data: PasswordResetConfirm) => authApi.confirmPasswordReset(data),
  })

// ─── Email Config Hooks ───────────────────────────────────────────────────────

export const useEmailConfigs = () =>
  useQuery({
    queryKey: ['email-configs'],
    queryFn: adminApi.listEmailConfigs,
    staleTime: 60_000,
  })

export const useCreateEmailConfig = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: CreateEmailConfigRequest) => adminApi.createEmailConfig(data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['email-configs'] }),
  })
}

export const useUpdateEmailConfig = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: UpdateEmailConfigRequest }) =>
      adminApi.updateEmailConfig(id, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['email-configs'] }),
  })
}

// ─── Bulk Upload Hooks ────────────────────────────────────────────────────────

export const useBulkUploadUsers = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (file: File) => adminApi.bulkUploadUsers(file),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['admin-users'] }),
  })
}

export const useUploadHierarchy = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (file: File) => adminApi.uploadHierarchy(file),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['organizations'] }),
  })
}

// ─── Permissions Hooks ────────────────────────────────────────────────────────

export const usePermissions = () =>
  useQuery({
    queryKey: ['permissions'],
    queryFn: adminApi.listPermissions,
    staleTime: 5 * 60_000,
  })

export const useUserGroupsDetail = () =>
  useQuery({
    queryKey: ['user-groups-detail'],
    queryFn: adminApi.listUserGroupsDetail,
    staleTime: 60_000,
  })

export const useSetGroupPermissions = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ groupId, data }: { groupId: string; data: { permission_codenames: string[] } }) =>
      adminApi.setGroupPermissions(groupId, data),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['user-groups-detail'] }),
  })
}

// ─── Pending Registrations Hooks ──────────────────────────────────────────────

export const usePendingRegistrations = () =>
  useQuery({
    queryKey: ['pending-registrations'],
    queryFn: adminApi.listPendingRegistrations,
    staleTime: 30_000,
  })

export const useApproveRegistration = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (userId: string) => adminApi.approveRegistration(userId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['pending-registrations'] })
      qc.invalidateQueries({ queryKey: ['admin-users'] })
    },
  })
}

export const useDeclineRegistration = () => {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (userId: string) => adminApi.declineRegistration(userId),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['pending-registrations'] }),
  })
}
