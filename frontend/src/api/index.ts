import { apiClient } from './client'
import type {
  AdminUserCreateRequest,
  AdminUserUpdateRequest,
  AppSetting,
  AssignableUser,
  AuthTokens,
  BulkUserUploadResult,
  ConfigItem,
  ConfigItemType,
  CreateCommentRequest,
  CreateConfigItemRequest,
  CreateEmailConfigRequest,
  CreateTicketRequest,
  EmailConfig,
  HierarchyUploadResult,
  KanbanBoard,
  LoginRequest,
  Organization,
  PasswordResetConfirm,
  PasswordResetRequest,
  PermissionInfo,
  RegisterRequest,
  Ticket,
  TicketSummary,
  TOTPSetupResponse,
  UpdateEmailConfigRequest,
  UpdateUserGroupsRequest,
  UpdateUserGroupRequest,
  UpdateWaitingForRequest,
  UserGroup,
  UserGroupDetail,
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

  requestPasswordReset: (data: PasswordResetRequest) =>
    apiClient.post<{ message: string; reset_token?: string }>('/auth/password-reset/request', data).then((r) => r.data),

  confirmPasswordReset: (data: PasswordResetConfirm) =>
    apiClient.post<{ message: string }>('/auth/password-reset/confirm', data).then((r) => r.data),

  logout: () =>
    apiClient.post<{ message: string }>('/auth/logout').then((r) => r.data),
}

// ─── Organizations ────────────────────────────────────────────────────────────

export const organizationsApi = {
  list: (params?: { level?: string; parent_id?: string }) =>
    apiClient.get<Organization[]>('/organizations/', { params }).then((r) => r.data),

  listLandesverbaende: () =>
    apiClient.get<Organization[]>('/organizations/landesverbaende').then((r) => r.data),

  listRegionalstellen: (landesverbandId?: string) =>
    apiClient
      .get<Organization[]>('/organizations/regionalstellen', {
        params: landesverbandId ? { landesverband_id: landesverbandId } : undefined,
      })
      .then((r) => r.data),

  listOrtsverbaende: (regionalstelleId?: string) =>
    apiClient
      .get<Organization[]>('/organizations/ortsverbaende', {
        params: regionalstelleId ? { regionalstelle_id: regionalstelleId } : undefined,
      })
      .then((r) => r.data),
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
  uploadAvatar: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return apiClient
      .post<User>('/users/me/avatar', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      .then((r) => r.data)
  },
  deleteAvatar: () => apiClient.delete<User>('/users/me/avatar').then((r) => r.data),
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

  listUsers: (filters?: { landesverband_id?: string; regionalstelle_id?: string; ortsverband_id?: string }) =>
    apiClient.get<User[]>('/admin/users', { params: filters }).then((r) => r.data),

  createUser: (data: AdminUserCreateRequest) =>
    apiClient.post<User>('/admin/users', data).then((r) => r.data),

  updateUser: (userId: string, data: AdminUserUpdateRequest) =>
    apiClient.patch<User>(`/admin/users/${userId}`, data).then((r) => r.data),

  listPermissions: () =>
    apiClient.get<PermissionInfo[]>('/admin/permissions').then((r) => r.data),

  listUserGroupsDetail: () =>
    apiClient.get<UserGroupDetail[]>('/admin/user-groups-detail').then((r) => r.data),

  setGroupPermissions: (groupId: string, data: { permission_codenames: string[] }) =>
    apiClient.put<UserGroupDetail>(`/admin/user-groups/${groupId}/permissions`, data).then((r) => r.data),

  listEmailConfigs: () =>
    apiClient.get<EmailConfig[]>('/admin/email-configs').then((r) => r.data),

  getEmailConfig: (orgId: string) =>
    apiClient.get<EmailConfig>(`/admin/email-configs/${orgId}`).then((r) => r.data),

  createEmailConfig: (data: CreateEmailConfigRequest) =>
    apiClient.post<EmailConfig>('/admin/email-configs', data).then((r) => r.data),

  updateEmailConfig: (configId: string, data: UpdateEmailConfigRequest) =>
    apiClient.patch<EmailConfig>(`/admin/email-configs/${configId}`, data).then((r) => r.data),

  bulkUploadUsers: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return apiClient
      .post<BulkUserUploadResult>('/admin/users/bulk-upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      .then((r) => r.data)
  },

  uploadHierarchy: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return apiClient
      .post<HierarchyUploadResult>('/admin/hierarchy/upload', formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      .then((r) => r.data)
  },

  listPendingRegistrations: () =>
    apiClient.get<User[]>('/admin/pending-registrations').then((r) => r.data),

  approveRegistration: (userId: string) =>
    apiClient.post<User>(`/admin/pending-registrations/${userId}/approve`).then((r) => r.data),

  declineRegistration: (userId: string) =>
    apiClient.post(`/admin/pending-registrations/${userId}/decline`).then((r) => r.data),
}
