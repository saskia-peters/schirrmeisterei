export type ConfigItemType = 'priority' | 'category' | 'group'

export interface ConfigItem {
  id: string
  type: ConfigItemType
  name: string
  sort_order: number
  is_active: boolean
  created_at: string
}

export interface CreateConfigItemRequest {
  type: ConfigItemType
  name: string
  sort_order?: number
}

export interface UpdateConfigItemRequest {
  name?: string
  sort_order?: number
  is_active?: boolean
}

export type TicketStatus = 'new' | 'working' | 'waiting' | 'resolved' | 'closed'

export type OrganizationLevel = 'ortsverband' | 'regionalstelle' | 'landesverband' | 'leitung'

export const ORG_LEVEL_ABBREV: Record<OrganizationLevel, string> = {
  ortsverband: 'OV',
  regionalstelle: 'Rst',
  landesverband: 'LV',
  leitung: 'LTG',
}

export interface Organization {
  id: string
  name: string
  level: OrganizationLevel
  parent_id: string | null
  created_at: string
}

export interface User {
  id: string
  email: string
  full_name: string
  is_active: boolean
  is_superuser: boolean
  force_password_change: boolean
  groups: string[]
  totp_enabled: boolean
  avatar_url: string | null
  organization_id: string | null
  organization_name: string | null
  organization_level: OrganizationLevel | null
  org_abbrev: string | null
  created_at: string
  updated_at: string
}

export interface AppSetting {
  key: string
  value: string
}

export type AgeThresholds = {
  age_green_days: number
  age_light_green_days: number
  age_yellow_days: number
  age_orange_days: number
  age_light_red_days: number
}

export interface UserGroup {
  id: string
  name: string
  created_at: string
}

export interface CreateUserGroupRequest {
  name: string
}

export interface UpdateUserGroupRequest {
  name: string
}

export interface UpdateUserGroupsRequest {
  group_names: string[]
}

export interface Attachment {
  id: string
  ticket_id: string
  filename: string
  content_type: string
  file_size: number
  uploaded_by_id: string
  created_at: string
  url: string
}

export interface Comment {
  id: string
  ticket_id: string
  author_id: string
  author_name: string
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

export interface Ticket {
  id: string
  title: string
  description: string
  status: TicketStatus
  creator_id: string
  assignee_id: string | null
  assignee_name: string | null
  organization_id: string | null
  priority_id: string | null
  priority_name: string | null
  category_id: string | null
  category_name: string | null
  affected_group_id: string | null
  affected_group_name: string | null
  waiting_for: string | null
  created_at: string
  updated_at: string
  attachments: Attachment[]
  comments: Comment[]
  status_logs: StatusLog[]
}

export interface TicketSummary {
  id: string
  title: string
  status: TicketStatus
  creator_id: string
  creator_name: string
  assignee_id: string | null
  assignee_name: string | null
  organization_id: string | null
  organization_name: string | null
  priority_id: string | null
  priority_name: string | null
  category_id: string | null
  category_name: string | null
  affected_group_id: string | null
  affected_group_name: string | null
  waiting_for: string | null
  created_at: string
  updated_at: string
}

export interface KanbanBoard {
  new: TicketSummary[]
  working: TicketSummary[]
  waiting: TicketSummary[]
  resolved: TicketSummary[]
  closed: TicketSummary[]
}

export interface AuthTokens {
  access_token: string
  refresh_token: string
  token_type: string
}

export interface LoginRequest {
  email: string
  password: string
  totp_code?: string
}

export interface RegisterRequest {
  email: string
  password: string
  full_name: string
  organization_id?: string
}

export interface AssignableUser {
  id: string
  full_name: string
}

export interface CreateTicketRequest {
  title: string
  description: string
  assignee_id?: string
  priority_id?: string
  category_id?: string
  affected_group_id?: string
}

export interface UpdateTicketRequest {
  title?: string
  description?: string
  assignee_id?: string | null
  priority_id?: string | null
  category_id?: string | null
  affected_group_id?: string | null
}

export interface UpdateTicketStatusRequest {
  status: TicketStatus
  note?: string
}

export interface CreateCommentRequest {
  content: string
}

export interface UpdateWaitingForRequest {
  waiting_for: string | null
}

export interface TOTPSetupResponse {
  secret: string
  qr_code_url: string
  provisioning_uri: string
}

export interface EmailConfig {
  id: string
  organization_id: string
  organization_name: string | null
  smtp_host: string
  smtp_port: number
  smtp_user: string
  from_email: string
  use_tls: boolean
  is_active: boolean
  created_at: string
  updated_at: string
}

export interface CreateEmailConfigRequest {
  organization_id: string
  smtp_host?: string
  smtp_port?: number
  smtp_user?: string
  smtp_password?: string
  from_email?: string
  use_tls?: boolean
  is_active?: boolean
}

export interface UpdateEmailConfigRequest {
  smtp_host?: string
  smtp_port?: number
  smtp_user?: string
  smtp_password?: string
  from_email?: string
  use_tls?: boolean
  is_active?: boolean
}

export interface BulkUserUploadResult {
  created: number
  errors: string[]
}

export interface HierarchyUploadResult {
  created: number
  skipped: number
  errors: string[]
}

export interface PermissionInfo {
  id: string
  codename: string
  description: string
}

export interface UserGroupDetail {
  id: string
  name: string
  permissions: string[]
  created_at: string
}

export interface PasswordResetRequest {
  email: string
}

export interface PasswordResetConfirm {
  token: string
  new_password: string
}
