import { apiClient } from './client'
import type {
  AppSetting,
  AssignableUser,
  AuthTokens,
  ConfigItem,
  ConfigItemType,
  CreateCommentRequest,
  CreateConfigItemRequest,
  CreateTicketRequest,
  KanbanBoard,
  LoginRequest,
  RegisterRequest,
  Ticket,
  TicketSummary,
  TOTPSetupResponse,
  UpdateUserGroupsRequest,
  UpdateUserGroupRequest,
  UpdateWaitingForRequest,
  UserGroup,
  CreateUserGroupRequest,
  UpdateConfigItemRequest,
  UpdateTicketRequest,
  UpdateTicketStatusRequest,
  User,
} from '@/types'

// ─── Auth ─────────────────────────────────────────────────────────────────────

export const authApi = {
  login: (data: LoginRequest) =>
    apiClient.post<AuthTokens>('/auth/login', data).then((r) => r.data),

  register: (data: RegisterRequest) =>
    apiClient.post<User>('/auth/register', data).then((r) => r.data),

  me: () => apiClient.get<User>('/auth/me').then((r) => r.data),

  setupTotp: () =>
    apiClient.post<TOTPSetupResponse>('/auth/totp/setup').then((r) => r.data),

  verifyTotp: (totp_code: string) =>
    apiClient.post('/auth/totp/verify', { totp_code }).then((r) => r.data),

  disableTotp: (totp_code: string) =>
    apiClient.delete('/auth/totp/disable', { data: { totp_code } }).then((r) => r.data),
}

// ─── Tickets ──────────────────────────────────────────────────────────────────

export const ticketsApi = {
  getBoard: () => apiClient.get<KanbanBoard>('/tickets/board').then((r) => r.data),

  list: (status?: string) =>
    apiClient
      .get<TicketSummary[]>('/tickets/', { params: status ? { status } : undefined })
      .then((r) => r.data),

  get: (id: string) => apiClient.get<Ticket>(`/tickets/${id}`).then((r) => r.data),

  create: (data: CreateTicketRequest) =>
    apiClient.post<Ticket>('/tickets/', data).then((r) => r.data),

  update: (id: string, data: UpdateTicketRequest) =>
    apiClient.patch<Ticket>(`/tickets/${id}`, data).then((r) => r.data),

  updateStatus: (id: string, data: UpdateTicketStatusRequest) =>
    apiClient.patch<Ticket>(`/tickets/${id}/status`, data).then((r) => r.data),

  delete: (id: string) => apiClient.delete(`/tickets/${id}`).then((r) => r.data),

  uploadAttachment: (ticketId: string, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return apiClient
      .post(`/tickets/${ticketId}/attachments`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      .then((r) => r.data)
  },

  deleteAttachment: (ticketId: string, attachmentId: string) =>
    apiClient.delete(`/tickets/${ticketId}/attachments/${attachmentId}`).then((r) => r.data),

  addComment: (ticketId: string, data: CreateCommentRequest) =>
    apiClient.post(`/tickets/${ticketId}/comments`, data).then((r) => r.data),

  deleteComment: (ticketId: string, commentId: string) =>
    apiClient.delete(`/tickets/${ticketId}/comments/${commentId}`).then((r) => r.data),

  updateWaitingFor: (ticketId: string, data: UpdateWaitingForRequest) =>
    apiClient.patch<Ticket>(`/tickets/${ticketId}/waiting-for`, data).then((r) => r.data),
}

// ─── Users ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

export const usersApi = {
  list: () => apiClient.get<User[]>('/users/').then((r) => r.data),
  get: (id: string) => apiClient.get<User>(`/users/${id}`).then((r) => r.data),
  assignable: () => apiClient.get<AssignableUser[]>('/users/assignable').then((r) => r.data),
  update: (id: string, data: { password?: string; full_name?: string }) =>
    apiClient.patch<User>(`/users/${id}`, data).then((r) => r.data),
}

// ─── Admin ────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────────

export const adminApi = {
  listConfigItems: (type?: ConfigItemType, includeInactive = false) =>
    apiClient
      .get<ConfigItem[]>('/admin/config-items', {
        params: { ...(type ? { type } : {}), include_inactive: includeInactive },
      })
      .then((r) => r.data),

  createConfigItem: (data: CreateConfigItemRequest) =>
    apiClient.post<ConfigItem>('/admin/config-items', data).then((r) => r.data),

  updateConfigItem: (id: string, data: UpdateConfigItemRequest) =>
    apiClient.patch<ConfigItem>(`/admin/config-items/${id}`, data).then((r) => r.data),

  deleteConfigItem: (id: string) =>
    apiClient.delete(`/admin/config-items/${id}`).then((r) => r.data),

  listUserGroups: () =>
    apiClient.get<UserGroup[]>('/admin/user-groups').then((r) => r.data),

  createUserGroup: (data: CreateUserGroupRequest) =>
    apiClient.post<UserGroup>('/admin/user-groups', data).then((r) => r.data),

  updateUserGroup: (id: string, data: UpdateUserGroupRequest) =>
    apiClient.patch<UserGroup>(`/admin/user-groups/${id}`, data).then((r) => r.data),

  deleteUserGroup: (id: string) =>
    apiClient.delete(`/admin/user-groups/${id}`).then((r) => r.data),

  getUserGroups: (userId: string) =>
    apiClient.get<string[]>(`/admin/users/${userId}/groups`).then((r) => r.data),

  setUserGroups: (userId: string, data: UpdateUserGroupsRequest) =>
    apiClient.put<string[]>(`/admin/users/${userId}/groups`, data).then((r) => r.data),

  getAppSettings: () =>
    apiClient.get<AppSetting[]>('/admin/app-settings').then((r) => r.data),

  updateAppSetting: (key: string, data: { value: string }) =>
    apiClient.patch<AppSetting>(`/admin/app-settings/${key}`, data).then((r) => r.data),

  listUsers: () =>
    apiClient.get<User[]>('/admin/users').then((r) => r.data),
}
