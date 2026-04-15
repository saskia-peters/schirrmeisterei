import { useState, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import { toast } from 'sonner'
import {
  useConfigItems,
  useCreateConfigItem,
  useUpdateConfigItem,
  useDeleteConfigItem,
  useUserGroups,
  useCreateUserGroup,
  useUpdateUserGroup,
  useDeleteUserGroup,
  useSetUserGroups,
  useAppSettings,
  useUpdateAppSetting,
  useAdminUsers,
  useCreateAdminUser,
  useUpdateAdminUser,
  useEmailConfigs,
  useCreateEmailConfig,
  useUpdateEmailConfig,
  useOrganizations,
  useLandesverbaende,
  useRegionalstellen,
  useOrtsverbaende,
  useBulkUploadUsers,
  useUploadHierarchy,
  usePermissions,
  useUserGroupsDetail,
  useSetGroupPermissions,
  usePendingRegistrations,
  useApproveRegistration,
  useDeclineRegistration,
} from '@/hooks/useApi'
import { useAuthStore } from '@/store/authStore'
import type { ConfigItem, ConfigItemType, EmailConfig, User, UserGroup } from '@/types'

type AdminTab = ConfigItemType | 'user-roles' | 'age-thresholds' | 'users' | 'email-config' | 'bulk-upload' | 'role-permissions' | 'hierarchy' | 'registrations'

const BASE_TABS: { type: AdminTab; label: string }[] = [
  { type: 'priority', label: 'Priorities' },
  { type: 'category', label: 'Categories' },
  { type: 'group', label: 'Affected Groups' },
  { type: 'user-roles', label: 'User Roles' },
  { type: 'role-permissions', label: 'Role Permissions' },
  { type: 'age-thresholds', label: 'Age Thresholds' },
]

export function AdminPanel() {
  const { user } = useAuthStore()
  const navigate = useNavigate()
  const [activeTab, setActiveTab] = useState<AdminTab>('priority')
  const isSuperuser = user?.is_superuser ?? false
  const isAdmin = user?.groups?.includes('admin') ?? false

  const tabs = [
    ...BASE_TABS,
    ...(isAdmin || isSuperuser
      ? [
          { type: 'registrations' as AdminTab, label: 'Registrations' },
          { type: 'users' as AdminTab, label: 'Users' },
          { type: 'email-config' as AdminTab, label: 'Email Config' },
          { type: 'bulk-upload' as AdminTab, label: 'Bulk Upload' },
          { type: 'hierarchy' as AdminTab, label: 'Hierarchy Import' },
        ]
      : []),
  ]

  return (
    <div className="admin-page">
      <div className="admin-page-header">
        <h1>Administration</h1>
        <button className="btn btn-secondary btn-sm" onClick={() => navigate('/')}>
          ← Back to Board
        </button>
      </div>

      <div className="admin-tabs">
        {tabs.map((tab) => (
          <button
            key={tab.type}
            className={`admin-tab ${activeTab === tab.type ? 'admin-tab--active' : ''}`}
            onClick={() => setActiveTab(tab.type)}
          >
            {tab.label}
          </button>
        ))}
      </div>

      <div className="admin-tab-content">
        {activeTab === 'registrations'
          ? <PendingRegistrationsAdmin />
          : activeTab === 'users'
          ? <UserOverview />
          : activeTab === 'user-roles'
          ? <UserRoleAdmin />
          : activeTab === 'role-permissions'
          ? <RolePermissionsAdmin />
          : activeTab === 'age-thresholds'
          ? <AgeThresholdsAdmin isSuperuser={isSuperuser} />
          : activeTab === 'email-config'
          ? <EmailConfigAdmin />
          : activeTab === 'bulk-upload'
          ? <BulkUploadAdmin />
          : activeTab === 'hierarchy'
          ? <HierarchyUploadAdmin />
          : <ConfigItemList type={activeTab as ConfigItemType} isSuperuser={isSuperuser} />}
      </div>
    </div>
  )
}

function ConfigItemList({ type, isSuperuser }: { type: ConfigItemType; isSuperuser: boolean }) {
  const { data: items = [], isLoading } = useConfigItems(type, true)
  const createItem = useCreateConfigItem()
  const updateItem = useUpdateConfigItem()
  const deleteItem = useDeleteConfigItem()

  const [newName, setNewName] = useState('')
  const [editingId, setEditingId] = useState<string | null>(null)
  const [editName, setEditName] = useState('')

  const handleCreate = async () => {
    const name = newName.trim()
    if (!name) return
    try {
      await createItem.mutateAsync({ type, name, sort_order: items.length })
      setNewName('')
      toast.success('Item created')
    } catch {
      toast.error('Failed to create item')
    }
  }

  const handleStartEdit = (item: ConfigItem) => {
    setEditingId(item.id)
    setEditName(item.name)
  }

  const handleSaveEdit = async (id: string) => {
    const name = editName.trim()
    if (!name) return
    try {
      await updateItem.mutateAsync({ id, data: { name } })
      setEditingId(null)
      toast.success('Item updated')
    } catch {
      toast.error('Failed to update item')
    }
  }

  const handleToggleActive = async (item: ConfigItem) => {
    try {
      await updateItem.mutateAsync({ id: item.id, data: { is_active: !item.is_active } })
      toast.success(item.is_active ? 'Item deactivated' : 'Item activated')
    } catch {
      toast.error('Failed to update item')
    }
  }

  const handleDelete = async (id: string) => {
    if (!window.confirm('Delete this item? Existing tickets using it will keep the reference.')) return
    try {
      await deleteItem.mutateAsync(id)
      toast.success('Item deleted')
    } catch {
      toast.error('Failed to delete item')
    }
  }

  if (isLoading) return <p className="admin-loading">Loading…</p>

  return (
    <div className="config-item-list">
      <table className="admin-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Order</th>
            <th>Active</th>
            {isSuperuser && <th>Actions</th>}
          </tr>
        </thead>
        <tbody>
          {items.map((item) => (
            <tr key={item.id} className={item.is_active ? '' : 'row-inactive'}>
              <td>
                {editingId === item.id ? (
                  <input
                    value={editName}
                    onChange={(e) => setEditName(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleSaveEdit(item.id)}
                    autoFocus
                    className="admin-inline-input"
                  />
                ) : (
                  item.name
                )}
              </td>
              <td>{item.sort_order}</td>
              <td>
                {isSuperuser ? (
                  <button
                    className={`btn btn-sm ${item.is_active ? 'btn-ghost' : 'btn-secondary'}`}
                    onClick={() => handleToggleActive(item)}
                    title={item.is_active ? 'Deactivate' : 'Activate'}
                  >
                    {item.is_active ? '✓ Active' : '✗ Inactive'}
                  </button>
                ) : (
                  item.is_active ? '✓' : '✗'
                )}
              </td>
              {isSuperuser && (
                <td className="admin-actions">
                  {editingId === item.id ? (
                    <>
                      <button className="btn btn-sm btn-primary" onClick={() => handleSaveEdit(item.id)}>Save</button>
                      <button className="btn btn-sm btn-ghost" onClick={() => setEditingId(null)}>Cancel</button>
                    </>
                  ) : (
                    <>
                      <button className="btn btn-sm btn-secondary" onClick={() => handleStartEdit(item)}>Rename</button>
                      <button className="btn btn-sm btn-danger" onClick={() => handleDelete(item.id)}>Delete</button>
                    </>
                  )}
                </td>
              )}
            </tr>
          ))}
          {items.length === 0 && (
            <tr><td colSpan={isSuperuser ? 4 : 3} className="admin-empty">No items yet.</td></tr>
          )}
        </tbody>
      </table>

      {isSuperuser && (
        <div className="admin-add-row">
          <input
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && handleCreate()}
            placeholder="New item name…"
            className="admin-inline-input"
          />
          <button
            className="btn btn-primary btn-sm"
            onClick={handleCreate}
            disabled={!newName.trim() || createItem.isPending}
          >
            + Add
          </button>
        </div>
      )}
    </div>
  )
}

function UserRoleAdmin() {
  const { user: currentUser } = useAuthStore()
  const { data: users = [] } = useAdminUsers()
  const { data: groups = [] } = useUserGroups(true)

  const createGroup = useCreateUserGroup()
  const updateGroup = useUpdateUserGroup()
  const deleteGroup = useDeleteUserGroup()
  const setUserGroups = useSetUserGroups()

  const [newGroupName, setNewGroupName] = useState('')
  const [editingGroupId, setEditingGroupId] = useState<string | null>(null)
  const [editingGroupName, setEditingGroupName] = useState('')
  const [newRoleGroup, setNewRoleGroup] = useState<UserGroup | null>(null)

  const coreGroups = new Set(['helfende', 'schirrmeister', 'admin'])
  const sortedGroups = [...groups].sort((a, b) => a.name.localeCompare(b.name))

  const handleCreateGroup = async () => {
    const name = newGroupName.trim().toLowerCase()
    if (!name) return
    try {
      const created = await createGroup.mutateAsync({ name })
      setNewGroupName('')
      setNewRoleGroup(created)
      toast.success('Role group created')
    } catch {
      toast.error('Failed to create role group')
    }
  }

  const handleRenameGroup = async (groupId: string) => {
    const name = editingGroupName.trim().toLowerCase()
    if (!name) return
    try {
      await updateGroup.mutateAsync({ id: groupId, data: { name } })
      setEditingGroupId(null)
      setEditingGroupName('')
      toast.success('Role group renamed')
    } catch {
      toast.error('Failed to rename role group')
    }
  }

  const handleDeleteGroup = async (group: UserGroup) => {
    if (!window.confirm(`Delete role group "${group.name}"?`)) return
    try {
      await deleteGroup.mutateAsync(group.id)
      toast.success('Role group deleted')
    } catch {
      toast.error('Failed to delete role group')
    }
  }

  const handleToggleUserGroup = async (user: User, groupName: string, checked: boolean) => {
    const next = new Set(user.groups)
    if (checked) {
      next.add(groupName)
    } else {
      next.delete(groupName)
    }
    next.add('helfende')
    try {
      await setUserGroups.mutateAsync({ userId: user.id, data: { group_names: [...next] } })
      toast.success(`Updated roles for ${user.full_name}`)
    } catch {
      toast.error('Failed to update user roles')
    }
  }

  return (
    <div className="user-role-admin">
      <h3>Role Groups</h3>
      <table className="admin-table">
        <thead>
          <tr>
            <th>Group</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {sortedGroups.map((group) => (
            <tr key={group.id}>
              <td>
                {editingGroupId === group.id ? (
                  <input
                    className="admin-inline-input"
                    value={editingGroupName}
                    onChange={(e) => setEditingGroupName(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleRenameGroup(group.id)}
                    autoFocus
                  />
                ) : (
                  group.name
                )}
              </td>
              <td className="admin-actions">
                {editingGroupId === group.id ? (
                  <>
                    <button className="btn btn-sm btn-primary" onClick={() => handleRenameGroup(group.id)}>Save</button>
                    <button className="btn btn-sm btn-ghost" onClick={() => setEditingGroupId(null)}>Cancel</button>
                  </>
                ) : (
                  <>
                    <button
                      className="btn btn-sm btn-secondary"
                      onClick={() => {
                        setEditingGroupId(group.id)
                        setEditingGroupName(group.name)
                      }}
                      disabled={group.name === 'helfende'}
                    >
                      Rename
                    </button>
                    <button
                      className="btn btn-sm btn-danger"
                      onClick={() => handleDeleteGroup(group)}
                      disabled={coreGroups.has(group.name)}
                    >
                      Delete
                    </button>
                  </>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <div className="admin-add-row">
        <input
          className="admin-inline-input"
          placeholder="New role group..."
          value={newGroupName}
          onChange={(e) => setNewGroupName(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && handleCreateGroup()}
        />
        <button className="btn btn-sm btn-primary" onClick={handleCreateGroup}>+ Add Group</button>
      </div>

      <h3 className="admin-subtitle">User Assignments</h3>
      <table className="admin-table">
        <thead>
          <tr>
            <th>User</th>
            {sortedGroups.map((group) => (
              <th key={group.id}>{group.name}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.id}>
              <td>{u.full_name}</td>
              {sortedGroups.map((group) => {
                const checked = u.groups.includes(group.name)
                const isHelfende = group.name === 'helfende'
                const isSelfAdmin = group.name === 'admin' && u.id === currentUser?.id
                return (
                  <td key={`${u.id}-${group.id}`}>
                    <input
                      type="checkbox"
                      checked={checked || isHelfende}
                      disabled={isHelfende || isSelfAdmin}
                      onChange={(e) => handleToggleUserGroup(u, group.name, e.target.checked)}
                    />
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>

      {newRoleGroup && (
        <NewRolePermissionsModal
          group={newRoleGroup}
          onClose={() => setNewRoleGroup(null)}
        />
      )}
    </div>
  )
}

function NewRolePermissionsModal({ group, onClose }: { group: UserGroup; onClose: () => void }) {
  const { data: allPermissions = [], isLoading } = usePermissions()
  const setGroupPerms = useSetGroupPermissions()
  const [availableSelected, setAvailableSelected] = useState<string[]>([])
  const [assignedSelected, setAssignedSelected] = useState<string[]>([])
  const [assignedCodenames, setAssignedCodenames] = useState<Set<string>>(new Set())

  const availablePerms = allPermissions.filter((p) => !assignedCodenames.has(p.codename))
  const assignedPerms = allPermissions.filter((p) => assignedCodenames.has(p.codename))

  const handleAdd = () => {
    setAssignedCodenames((prev) => {
      const next = new Set(prev)
      availableSelected.forEach((c) => next.add(c))
      return next
    })
    setAvailableSelected([])
  }

  const handleRemove = () => {
    setAssignedCodenames((prev) => {
      const next = new Set(prev)
      assignedSelected.forEach((c) => next.delete(c))
      return next
    })
    setAssignedSelected([])
  }

  const handleSave = async () => {
    try {
      await setGroupPerms.mutateAsync({
        groupId: group.id,
        data: { permission_codenames: [...assignedCodenames] },
      })
      toast.success('Permissions saved')
      onClose()
    } catch {
      toast.error('Failed to save permissions')
    }
  }

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal" role="dialog" aria-modal aria-label="Set Role Permissions">
        <div className="modal-header">
          <h2>Set Permissions — {group.name}</h2>
          <button className="modal-close" onClick={onClose} aria-label="Close">✕</button>
        </div>
        {isLoading ? (
          <p className="admin-loading" style={{ padding: '1.25rem' }}>Loading permissions…</p>
        ) : (
          <>
            <div className="modal-body">
              <div className="dual-listbox">
                <div className="dual-listbox-panel">
                  <h4>Available Permissions</h4>
                  <select
                    multiple
                    className="dual-listbox-select"
                    value={availableSelected}
                    onChange={(e) =>
                      setAvailableSelected(Array.from(e.target.selectedOptions, (o) => o.value))
                    }
                  >
                    {availablePerms.map((p) => (
                      <option key={p.id} value={p.codename} title={p.description}>
                        {p.codename}
                      </option>
                    ))}
                  </select>
                </div>
                <div className="dual-listbox-controls">
                  <button
                    className="btn btn-primary btn-sm"
                    onClick={handleAdd}
                    disabled={availableSelected.length === 0}
                    title="Add selected permissions"
                  >
                    →
                  </button>
                  <button
                    className="btn btn-primary btn-sm"
                    onClick={handleRemove}
                    disabled={assignedSelected.length === 0}
                    title="Remove selected permissions"
                  >
                    ←
                  </button>
                </div>
                <div className="dual-listbox-panel">
                  <h4>Assigned Permissions</h4>
                  <select
                    multiple
                    className="dual-listbox-select"
                    value={assignedSelected}
                    onChange={(e) =>
                      setAssignedSelected(Array.from(e.target.selectedOptions, (o) => o.value))
                    }
                  >
                    {assignedPerms.map((p) => (
                      <option key={p.id} value={p.codename} title={p.description}>
                        {p.codename}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-ghost btn-sm" onClick={onClose}>Skip</button>
              <button
                className="btn btn-primary btn-sm"
                onClick={handleSave}
                disabled={setGroupPerms.isPending}
              >
                {setGroupPerms.isPending ? 'Saving…' : 'Save Permissions'}
              </button>
            </div>
          </>
        )}
      </div>
    </div>
  )
}

const AGE_THRESHOLD_META: { key: string; label: string; description: string }[] = [
  { key: 'age_green_days', label: 'Dark Green up to (days)', description: 'Tickets up to this many days old show a dark green bar.' },
  { key: 'age_light_green_days', label: 'Light Green up to (days)', description: 'Tickets up to this many days old show a light green bar.' },
  { key: 'age_yellow_days', label: 'Yellow up to (days)', description: 'Tickets up to this many days old show a yellow bar.' },
  { key: 'age_orange_days', label: 'Orange up to (days)', description: 'Tickets up to this many days old show an orange bar.' },
  { key: 'age_light_red_days', label: 'Light Red up to (days)', description: 'Tickets up to this many days old show a light red bar. Older tickets are dark red.' },
]

function AgeThresholdsAdmin({ isSuperuser }: { isSuperuser: boolean }) {
  const { data: settings = [], isLoading } = useAppSettings()
  const updateSetting = useUpdateAppSetting()
  const [drafts, setDrafts] = useState<Record<string, string>>({})

  if (isLoading) return <p className="admin-loading">Loading…</p>

  const getValue = (key: string) =>
    drafts[key] ?? settings.find((s) => s.key === key)?.value ?? ''

  const handleSave = async (key: string) => {
    const value = (drafts[key] ?? '').trim()
    if (!value) return
    try {
      await updateSetting.mutateAsync({ key, value })
      setDrafts((d) => { const n = { ...d }; delete n[key]; return n })
      toast.success('Threshold updated')
    } catch {
      toast.error('Failed to update threshold')
    }
  }

  return (
    <div className="age-thresholds-admin">
      <p className="age-thresholds-desc">
        Configure how many days until a ticket's age indicator changes color.
        Tickets older than the <em>Light Red</em> threshold will show a dark red bar.
      </p>
      <div className="age-swatch-preview">
        {['var(--age-dark-green)', 'var(--age-light-green)', 'var(--age-yellow)', 'var(--age-orange)', 'var(--age-light-red)', 'var(--age-dark-red)'].map((c) => (
          <span key={c} className="age-swatch" style={{ background: c }} />
        ))}
      </div>
      <table className="admin-table age-thresholds-table">
        <thead>
          <tr>
            <th>Color range</th>
            <th>Max days</th>
            {isSuperuser && <th>Actions</th>}
          </tr>
        </thead>
        <tbody>
          {AGE_THRESHOLD_META.map(({ key, label, description }) => (
            <tr key={key}>
              <td title={description}>{label}</td>
              <td>
                <input
                  type="number"
                  min={1}
                  value={getValue(key)}
                  onChange={(e) => isSuperuser && setDrafts((d) => ({ ...d, [key]: e.target.value }))}
                  disabled={!isSuperuser}
                  className="admin-inline-input age-threshold-input"
                  onKeyDown={(e) => e.key === 'Enter' && isSuperuser && handleSave(key)}
                />
              </td>
              {isSuperuser && (
                <td className="admin-actions">
                  <button
                    className="btn btn-sm btn-primary"
                    onClick={() => handleSave(key)}
                    disabled={!drafts[key] || updateSetting.isPending}
                  >
                    Save
                  </button>
                </td>
              )}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function UserOverview() {
  const { user: currentUser } = useAuthStore()
  const [filterLV, setFilterLV] = useState<string>('')
  const [filterRSt, setFilterRSt] = useState<string>('')
  const [filterOV, setFilterOV] = useState<string>('')

  const filters = {
    ...(filterOV ? { ortsverband_id: filterOV } : filterRSt ? { regionalstelle_id: filterRSt } : filterLV ? { landesverband_id: filterLV } : {}),
  }
  const { data: users = [], isLoading } = useAdminUsers(Object.keys(filters).length > 0 ? filters : undefined)

  const { data: landesverbaende = [] } = useLandesverbaende()
  const { data: regionalstellen = [] } = useRegionalstellen(filterLV || undefined)
  const { data: ortsverbaende = [] } = useOrtsverbaende(filterRSt || undefined)
  const { data: allOrgs = [] } = useOrganizations()
  const { data: groups = [] } = useUserGroups(true)

  const createUser = useCreateAdminUser()
  const updateUser = useUpdateAdminUser()

  const [showCreate, setShowCreate] = useState(false)
  const [editingUserId, setEditingUserId] = useState<string | null>(null)

  const emptyCreateForm = {
    email: '',
    full_name: '',
    password: '',
    organization_id: '',
    is_active: true,
    group_names: [] as string[],
  }
  const [createForm, setCreateForm] = useState(emptyCreateForm)

  const emptyEditForm = {
    full_name: '',
    password: '',
    is_active: true,
    organization_id: '',
    group_names: [] as string[],
  }
  const [editForm, setEditForm] = useState(emptyEditForm)

  const handleCreate = async () => {
    if (!createForm.email || !createForm.full_name || !createForm.password || !createForm.organization_id) {
      toast.error('Please fill in all required fields')
      return
    }
    try {
      await createUser.mutateAsync({
        email: createForm.email,
        full_name: createForm.full_name,
        password: createForm.password,
        organization_id: createForm.organization_id,
        is_active: createForm.is_active,
        group_names: createForm.group_names.length > 0 ? createForm.group_names : undefined,
      })
      setCreateForm(emptyCreateForm)
      setShowCreate(false)
      toast.success('User created')
    } catch {
      toast.error('Failed to create user')
    }
  }

  const handleStartEdit = (user: User) => {
    setEditingUserId(user.id)
    setEditForm({
      full_name: user.full_name,
      password: '',
      is_active: user.is_active,
      organization_id: user.organization_id ?? '',
      group_names: [...user.groups],
    })
  }

  const handleSaveEdit = async () => {
    if (!editingUserId) return
    try {
      await updateUser.mutateAsync({
        userId: editingUserId,
        data: {
          full_name: editForm.full_name || undefined,
          password: editForm.password || undefined,
          is_active: editForm.is_active,
          organization_id: editForm.organization_id || undefined,
          group_names: editForm.group_names,
        },
      })
      setEditingUserId(null)
      toast.success('User updated')
    } catch {
      toast.error('Failed to update user')
    }
  }

  const handleCancelEdit = () => {
    setEditingUserId(null)
    setEditForm(emptyEditForm)
  }

  const toggleEditGroup = (groupName: string) => {
    if (groupName === 'helfende') return
    if (groupName === 'admin' && editingUserId === currentUser?.id) return
    setEditForm((f) => ({
      ...f,
      group_names: f.group_names.includes(groupName)
        ? f.group_names.filter((g) => g !== groupName)
        : [...f.group_names, groupName],
    }))
  }

  const toggleCreateGroup = (groupName: string) => {
    if (groupName === 'helfende') return
    setCreateForm((f) => ({
      ...f,
      group_names: f.group_names.includes(groupName)
        ? f.group_names.filter((g) => g !== groupName)
        : [...f.group_names, groupName],
    }))
  }

  const sortedGroups = [...groups].sort((a, b) => a.name.localeCompare(b.name))

  if (isLoading) return <p className="admin-loading">Loading…</p>

  return (
    <div className="user-overview">
      <div className="admin-section-header">
        <h3>User Management</h3>
        <button className="btn btn-primary btn-sm" onClick={() => { setCreateForm(emptyCreateForm); setShowCreate(true) }}>
          + Create User
        </button>
      </div>

      {/* Org hierarchy filters */}
      <div className="user-filters">
        <div className="form-group">
          <label>Landesverband</label>
          <select value={filterLV} onChange={(e) => { setFilterLV(e.target.value); setFilterRSt(''); setFilterOV('') }}>
            <option value="">All</option>
            {landesverbaende.map((o) => (
              <option key={o.id} value={o.id}>{o.name}</option>
            ))}
          </select>
        </div>
        <div className="form-group">
          <label>Regionalstelle</label>
          <select value={filterRSt} onChange={(e) => { setFilterRSt(e.target.value); setFilterOV('') }} disabled={!filterLV}>
            <option value="">All</option>
            {regionalstellen.map((o) => (
              <option key={o.id} value={o.id}>{o.name}</option>
            ))}
          </select>
        </div>
        <div className="form-group">
          <label>Ortsverband</label>
          <select value={filterOV} onChange={(e) => setFilterOV(e.target.value)} disabled={!filterRSt}>
            <option value="">All</option>
            {ortsverbaende.map((o) => (
              <option key={o.id} value={o.id}>{o.name}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Create user form */}
      {showCreate && (
        <div className="user-edit-form">
          <h4>Create New User</h4>
          <div className="form-grid">
            <div className="form-group">
              <label>Email *</label>
              <input type="email" value={createForm.email} onChange={(e) => setCreateForm({ ...createForm, email: e.target.value })} placeholder="user@example.com" />
            </div>
            <div className="form-group">
              <label>Full Name *</label>
              <input value={createForm.full_name} onChange={(e) => setCreateForm({ ...createForm, full_name: e.target.value })} placeholder="Full Name" />
            </div>
            <div className="form-group">
              <label>Password *</label>
              <input type="password" value={createForm.password} onChange={(e) => setCreateForm({ ...createForm, password: e.target.value })} placeholder="Min. 8 characters" />
            </div>
            <div className="form-group">
              <label>Organization *</label>
              <select value={createForm.organization_id} onChange={(e) => setCreateForm({ ...createForm, organization_id: e.target.value })}>
                <option value="">-- Select --</option>
                {allOrgs.map((o) => (
                  <option key={o.id} value={o.id}>{o.name}</option>
                ))}
              </select>
            </div>
            <div className="form-group form-group-checkbox">
              <label><input type="checkbox" checked={createForm.is_active} onChange={(e) => setCreateForm({ ...createForm, is_active: e.target.checked })} /> Active</label>
            </div>
          </div>
          {sortedGroups.length > 0 && (
            <div className="form-group">
              <label>Roles</label>
              <div className="role-checkboxes">
                {sortedGroups.map((g) => (
                  <label key={g.id} className="role-checkbox-label">
                    <input
                      type="checkbox"
                      checked={createForm.group_names.includes(g.name) || g.name === 'helfende'}
                      disabled={g.name === 'helfende'}
                      onChange={() => toggleCreateGroup(g.name)}
                    />
                    {g.name}
                  </label>
                ))}
              </div>
            </div>
          )}
          <div className="form-actions">
            <button className="btn btn-primary btn-sm" onClick={handleCreate} disabled={createUser.isPending}>Create</button>
            <button className="btn btn-ghost btn-sm" onClick={() => setShowCreate(false)}>Cancel</button>
          </div>
        </div>
      )}

      <table className="admin-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Email</th>
            <th>Organization</th>
            <th>Roles</th>
            <th>Active</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {users.map((u) =>
            editingUserId === u.id ? (
              <tr key={u.id} className="editing-row">
                <td colSpan={6}>
                  <div className="user-edit-form inline-edit">
                    <div className="form-grid">
                      <div className="form-group">
                        <label>Full Name</label>
                        <input value={editForm.full_name} onChange={(e) => setEditForm({ ...editForm, full_name: e.target.value })} />
                      </div>
                      <div className="form-group">
                        <label>New Password</label>
                        <input type="password" value={editForm.password} onChange={(e) => setEditForm({ ...editForm, password: e.target.value })} placeholder="Leave empty to keep" />
                      </div>
                      <div className="form-group">
                        <label>Organization</label>
                        <select value={editForm.organization_id} onChange={(e) => setEditForm({ ...editForm, organization_id: e.target.value })}>
                          <option value="">-- Select --</option>
                          {allOrgs.map((o) => (
                            <option key={o.id} value={o.id}>{o.name}</option>
                          ))}
                        </select>
                      </div>
                      <div className="form-group form-group-checkbox">
                        <label><input type="checkbox" checked={editForm.is_active} onChange={(e) => setEditForm({ ...editForm, is_active: e.target.checked })} /> Active</label>
                      </div>
                    </div>
                    {sortedGroups.length > 0 && (
                      <div className="form-group">
                        <label>Roles</label>
                        <div className="role-checkboxes">
                          {sortedGroups.map((g) => (
                            <label key={g.id} className="role-checkbox-label">
                              <input
                                type="checkbox"
                                checked={editForm.group_names.includes(g.name) || g.name === 'helfende'}
                                disabled={g.name === 'helfende' || (g.name === 'admin' && editingUserId === currentUser?.id)}
                                onChange={() => toggleEditGroup(g.name)}
                              />
                              {g.name}
                            </label>
                          ))}
                        </div>
                      </div>
                    )}
                    <div className="form-actions">
                      <button className="btn btn-primary btn-sm" onClick={handleSaveEdit} disabled={updateUser.isPending}>Save</button>
                      <button className="btn btn-ghost btn-sm" onClick={handleCancelEdit}>Cancel</button>
                    </div>
                  </div>
                </td>
              </tr>
            ) : (
              <tr key={u.id}>
                <td>
                  {u.full_name}
                  {u.org_abbrev && <span className="org-badge">({u.org_abbrev})</span>}
                </td>
                <td>{u.email}</td>
                <td>{u.organization_name ?? '—'}</td>
                <td>
                  <div className="role-badges">
                    {u.groups.map((g) => (
                      <span key={g} className="role-badge">{g}</span>
                    ))}
                  </div>
                </td>
                <td>{u.is_active ? '✓' : '✗'}</td>
                <td className="admin-actions">
                  <button className="btn btn-sm btn-secondary" onClick={() => handleStartEdit(u)}>Edit</button>
                </td>
              </tr>
            )
          )}
          {users.length === 0 && (
            <tr>
              <td colSpan={6} className="admin-empty">No users found.</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}

function EmailConfigAdmin() {
  const { data: configs = [], isLoading } = useEmailConfigs()
  const { data: orgs = [] } = useOrganizations({ level: 'ortsverband' })
  const createConfig = useCreateEmailConfig()
  const updateConfig = useUpdateEmailConfig()

  const [editingId, setEditingId] = useState<string | null>(null)
  const [showCreate, setShowCreate] = useState(false)
  const [form, setForm] = useState({
    organization_id: '',
    smtp_host: '',
    smtp_port: 587,
    smtp_user: '',
    smtp_password: '',
    from_email: '',
    use_tls: true,
    is_active: true,
  })

  const resetForm = () => {
    setForm({
      organization_id: '',
      smtp_host: '',
      smtp_port: 587,
      smtp_user: '',
      smtp_password: '',
      from_email: '',
      use_tls: true,
      is_active: true,
    })
  }

  const configuredOrgIds = new Set(configs.map((c) => c.organization_id))
  const availableOrgs = orgs.filter((o) => !configuredOrgIds.has(o.id))

  const handleCreate = async () => {
    if (!form.organization_id || !form.smtp_host) return
    try {
      await createConfig.mutateAsync({
        organization_id: form.organization_id,
        smtp_host: form.smtp_host,
        smtp_port: form.smtp_port,
        smtp_user: form.smtp_user,
        smtp_password: form.smtp_password,
        from_email: form.from_email,
        use_tls: form.use_tls,
        is_active: form.is_active,
      })
      resetForm()
      setShowCreate(false)
      toast.success('Email config created')
    } catch {
      toast.error('Failed to create email config')
    }
  }

  const handleStartEdit = (config: EmailConfig) => {
    setEditingId(config.id)
    setForm({
      organization_id: config.organization_id,
      smtp_host: config.smtp_host,
      smtp_port: config.smtp_port,
      smtp_user: config.smtp_user,
      smtp_password: '',
      from_email: config.from_email,
      use_tls: config.use_tls,
      is_active: config.is_active,
    })
  }

  const handleSaveEdit = async (id: string) => {
    try {
      await updateConfig.mutateAsync({
        id,
        data: {
          smtp_host: form.smtp_host,
          smtp_port: form.smtp_port,
          smtp_user: form.smtp_user,
          ...(form.smtp_password ? { smtp_password: form.smtp_password } : {}),
          from_email: form.from_email,
          use_tls: form.use_tls,
          is_active: form.is_active,
        },
      })
      setEditingId(null)
      resetForm()
      toast.success('Email config updated')
    } catch {
      toast.error('Failed to update email config')
    }
  }

  if (isLoading) return <p className="admin-loading">Loading…</p>

  return (
    <div className="email-config-admin">
      <div className="admin-section-header">
        <h3>Email Configuration per Ortsverband</h3>
        {availableOrgs.length > 0 && (
          <button className="btn btn-primary btn-sm" onClick={() => { resetForm(); setShowCreate(true) }}>
            + Add Config
          </button>
        )}
      </div>

      {showCreate && (
        <div className="email-config-form">
          <h4>New Email Config</h4>
          <div className="form-grid">
            <div className="form-group">
              <label>Organization</label>
              <select value={form.organization_id} onChange={(e) => setForm({ ...form, organization_id: e.target.value })}>
                <option value="">-- Select --</option>
                {availableOrgs.map((o) => (
                  <option key={o.id} value={o.id}>{o.name}</option>
                ))}
              </select>
            </div>
            <div className="form-group">
              <label>SMTP Host</label>
              <input value={form.smtp_host} onChange={(e) => setForm({ ...form, smtp_host: e.target.value })} placeholder="smtp.example.com" />
            </div>
            <div className="form-group">
              <label>SMTP Port</label>
              <input type="number" value={form.smtp_port} onChange={(e) => setForm({ ...form, smtp_port: Number(e.target.value) })} />
            </div>
            <div className="form-group">
              <label>SMTP User</label>
              <input value={form.smtp_user} onChange={(e) => setForm({ ...form, smtp_user: e.target.value })} />
            </div>
            <div className="form-group">
              <label>SMTP Password</label>
              <input type="password" value={form.smtp_password} onChange={(e) => setForm({ ...form, smtp_password: e.target.value })} />
            </div>
            <div className="form-group">
              <label>From Email</label>
              <input value={form.from_email} onChange={(e) => setForm({ ...form, from_email: e.target.value })} placeholder="noreply@example.com" />
            </div>
            <div className="form-group form-group-checkbox">
              <label><input type="checkbox" checked={form.use_tls} onChange={(e) => setForm({ ...form, use_tls: e.target.checked })} /> Use TLS</label>
            </div>
          </div>
          <div className="form-actions">
            <button className="btn btn-primary btn-sm" onClick={handleCreate} disabled={createConfig.isPending}>Save</button>
            <button className="btn btn-ghost btn-sm" onClick={() => setShowCreate(false)}>Cancel</button>
          </div>
        </div>
      )}

      <table className="admin-table">
        <thead>
          <tr>
            <th>Organization</th>
            <th>SMTP Host</th>
            <th>Port</th>
            <th>From</th>
            <th>TLS</th>
            <th>Active</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {configs.map((config) => (
            <tr key={config.id}>
              {editingId === config.id ? (
                <>
                  <td>{config.organization_name ?? config.organization_id}</td>
                  <td><input className="admin-inline-input" value={form.smtp_host} onChange={(e) => setForm({ ...form, smtp_host: e.target.value })} /></td>
                  <td><input className="admin-inline-input" type="number" value={form.smtp_port} onChange={(e) => setForm({ ...form, smtp_port: Number(e.target.value) })} style={{ width: '5em' }} /></td>
                  <td><input className="admin-inline-input" value={form.from_email} onChange={(e) => setForm({ ...form, from_email: e.target.value })} /></td>
                  <td><input type="checkbox" checked={form.use_tls} onChange={(e) => setForm({ ...form, use_tls: e.target.checked })} /></td>
                  <td><input type="checkbox" checked={form.is_active} onChange={(e) => setForm({ ...form, is_active: e.target.checked })} /></td>
                  <td className="admin-actions">
                    <button className="btn btn-sm btn-primary" onClick={() => handleSaveEdit(config.id)}>Save</button>
                    <button className="btn btn-sm btn-ghost" onClick={() => { setEditingId(null); resetForm() }}>Cancel</button>
                  </td>
                </>
              ) : (
                <>
                  <td>{config.organization_name ?? config.organization_id}</td>
                  <td>{config.smtp_host}</td>
                  <td>{config.smtp_port}</td>
                  <td>{config.from_email}</td>
                  <td>{config.use_tls ? '✓' : '✗'}</td>
                  <td>{config.is_active ? '✓' : '✗'}</td>
                  <td className="admin-actions">
                    <button className="btn btn-sm btn-secondary" onClick={() => handleStartEdit(config)}>Edit</button>
                  </td>
                </>
              )}
            </tr>
          ))}
          {configs.length === 0 && (
            <tr>
              <td colSpan={7} className="admin-empty">No email configurations yet.</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}

function BulkUploadAdmin() {
  const bulkUpload = useBulkUploadUsers()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [result, setResult] = useState<{
    created: number
    errors: string[]
  } | null>(null)

  const handleUpload = async () => {
    const file = fileInputRef.current?.files?.[0]
    if (!file) {
      toast.error('Please select an XLSX file')
      return
    }
    try {
      const res = await bulkUpload.mutateAsync(file)
      setResult(res)
      if (res.errors.length === 0) {
        toast.success(`${res.created} users created successfully`)
      } else {
        toast.warning(`${res.created} created, ${res.errors.length} errors`)
      }
    } catch {
      toast.error('Bulk upload failed')
    }
  }

  return (
    <div className="bulk-upload-admin">
      <h3>Bulk User Upload</h3>
      <p className="bulk-upload-desc">
        Upload an XLSX file with columns: <strong>email</strong>, <strong>full_name</strong>, <strong>password</strong>, and optionally <strong>organization_id</strong>.
        If organization_id is not provided, users will be assigned to your organization.
      </p>

      <div className="bulk-upload-controls">
        <input
          ref={fileInputRef}
          type="file"
          accept=".xlsx,.xls"
          className="file-input"
        />
        <button
          className="btn btn-primary"
          onClick={handleUpload}
          disabled={bulkUpload.isPending}
        >
          {bulkUpload.isPending ? 'Uploading…' : 'Upload & Create Users'}
        </button>
      </div>

      {result && (
        <div className="bulk-upload-result">
          <p className="bulk-upload-summary">
            ✓ {result.created} user(s) created
          </p>
          {result.errors.length > 0 && (
            <div className="bulk-upload-errors">
              <p>Errors:</p>
              <ul>
                {result.errors.map((err, i) => (
                  <li key={i}>{err}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function RolePermissionsAdmin() {
  const { data: allPermissions = [], isLoading: loadingPerms } = usePermissions()
  const { data: groupsDetail = [], isLoading: loadingGroups } = useUserGroupsDetail()
  const setGroupPerms = useSetGroupPermissions()

  const [selectedGroupId, setSelectedGroupId] = useState<string>('')
  const [availableSelected, setAvailableSelected] = useState<string[]>([])
  const [assignedSelected, setAssignedSelected] = useState<string[]>([])

  if (loadingPerms || loadingGroups) return <p className="admin-loading">Loading…</p>

  const selectedGroup = groupsDetail.find((g) => g.id === selectedGroupId)
  const assignedCodenames = new Set(selectedGroup?.permissions ?? [])

  const availablePerms = allPermissions.filter((p) => !assignedCodenames.has(p.codename))
  const assignedPerms = allPermissions.filter((p) => assignedCodenames.has(p.codename))

  const handleAdd = async () => {
    if (!selectedGroupId || availableSelected.length === 0) return
    const newPerms = [...(selectedGroup?.permissions ?? []), ...availableSelected]
    try {
      await setGroupPerms.mutateAsync({ groupId: selectedGroupId, data: { permission_codenames: newPerms } })
      setAvailableSelected([])
      toast.success('Permissions added')
    } catch {
      toast.error('Failed to update permissions')
    }
  }

  const handleRemove = async () => {
    if (!selectedGroupId || assignedSelected.length === 0) return
    const removeSet = new Set(assignedSelected)
    const newPerms = (selectedGroup?.permissions ?? []).filter((p) => !removeSet.has(p))
    try {
      await setGroupPerms.mutateAsync({ groupId: selectedGroupId, data: { permission_codenames: newPerms } })
      setAssignedSelected([])
      toast.success('Permissions removed')
    } catch {
      toast.error('Failed to update permissions')
    }
  }

  return (
    <div className="role-permissions-admin">
      <div className="form-group">
        <label htmlFor="role-select">Select Role</label>
        <select
          id="role-select"
          value={selectedGroupId}
          onChange={(e) => {
            setSelectedGroupId(e.target.value)
            setAvailableSelected([])
            setAssignedSelected([])
          }}
        >
          <option value="">-- Select a role --</option>
          {groupsDetail.map((g) => (
            <option key={g.id} value={g.id}>{g.name}</option>
          ))}
        </select>
      </div>

      {selectedGroupId && (
        <div className="dual-listbox">
          <div className="dual-listbox-panel">
            <h4>Available Permissions</h4>
            <select
              multiple
              className="dual-listbox-select"
              value={availableSelected}
              onChange={(e) =>
                setAvailableSelected(Array.from(e.target.selectedOptions, (o) => o.value))
              }
            >
              {availablePerms.map((p) => (
                <option key={p.id} value={p.codename} title={p.description}>
                  {p.codename}
                </option>
              ))}
            </select>
          </div>

          <div className="dual-listbox-controls">
            <button
              className="btn btn-primary btn-sm"
              onClick={handleAdd}
              disabled={availableSelected.length === 0 || setGroupPerms.isPending}
              title="Add selected permissions"
            >
              →
            </button>
            <button
              className="btn btn-primary btn-sm"
              onClick={handleRemove}
              disabled={assignedSelected.length === 0 || setGroupPerms.isPending}
              title="Remove selected permissions"
            >
              ←
            </button>
          </div>

          <div className="dual-listbox-panel">
            <h4>Assigned Permissions</h4>
            <select
              multiple
              className="dual-listbox-select"
              value={assignedSelected}
              onChange={(e) =>
                setAssignedSelected(Array.from(e.target.selectedOptions, (o) => o.value))
              }
            >
              {assignedPerms.map((p) => (
                <option key={p.id} value={p.codename} title={p.description}>
                  {p.codename}
                </option>
              ))}
            </select>
          </div>
        </div>
      )}
    </div>
  )
}

function HierarchyUploadAdmin() {
  const uploadHierarchy = useUploadHierarchy()
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [result, setResult] = useState<{
    created: number
    skipped: number
    errors: string[]
  } | null>(null)

  const handleUpload = async () => {
    const file = fileInputRef.current?.files?.[0]
    if (!file) {
      toast.error('Please select an XLSX file')
      return
    }
    try {
      const res = await uploadHierarchy.mutateAsync(file)
      setResult(res)
      if (res.errors.length === 0) {
        toast.success(`${res.created} org(s) created, ${res.skipped} skipped`)
      } else {
        toast.warning(`${res.created} created, ${res.skipped} skipped, ${res.errors.length} errors`)
      }
    } catch {
      toast.error('Hierarchy upload failed')
    }
  }

  return (
    <div className="bulk-upload-admin">
      <h3>Import Organisation Hierarchy</h3>
      <p className="bulk-upload-desc">
        Upload an XLSX file with columns: <strong>level</strong> (<code>ortsverband</code>, <code>regionalstelle</code>, <code>landesverband</code>, <code>leitung</code>),{' '}
        <strong>name</strong>, and optionally <strong>parent_name</strong>.
        Existing organisations are skipped automatically.
      </p>

      <div className="bulk-upload-controls">
        <input
          ref={fileInputRef}
          type="file"
          accept=".xlsx,.xls"
          className="file-input"
        />
        <button
          className="btn btn-primary"
          onClick={handleUpload}
          disabled={uploadHierarchy.isPending}
        >
          {uploadHierarchy.isPending ? 'Uploading…' : 'Upload & Import'}
        </button>
      </div>

      {result && (
        <div className="bulk-upload-result">
          <p className="bulk-upload-summary">
            ✓ {result.created} org(s) created, {result.skipped} skipped
          </p>
          {result.errors.length > 0 && (
            <div className="bulk-upload-errors">
              <p>Errors:</p>
              <ul>
                {result.errors.map((err, i) => (
                  <li key={i}>{err}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  )
}

function PendingRegistrationsAdmin() {
  const { data: pending = [], isLoading } = usePendingRegistrations()
  const approve = useApproveRegistration()
  const decline = useDeclineRegistration()

  const handleApprove = async (userId: string) => {
    try {
      await approve.mutateAsync(userId)
      toast.success('Registration approved')
    } catch {
      toast.error('Failed to approve registration')
    }
  }

  const handleDecline = async (userId: string) => {
    if (!confirm('Are you sure you want to decline and delete this registration?')) return
    try {
      await decline.mutateAsync(userId)
      toast.success('Registration declined')
    } catch {
      toast.error('Failed to decline registration')
    }
  }

  if (isLoading) return <p>Loading…</p>

  if (pending.length === 0) {
    return <p className="text-muted">No pending registrations.</p>
  }

  return (
    <div className="admin-section">
      <h3>Pending Registrations ({pending.length})</h3>
      <table className="admin-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Email</th>
            <th>Organization</th>
            <th>Registered</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          {pending.map((user) => (
            <tr key={user.id}>
              <td>{user.full_name}</td>
              <td>{user.email}</td>
              <td>
                {user.organization_name
                  ? `${user.organization_name}${user.org_abbrev ? ` (${user.org_abbrev})` : ''}`
                  : '—'}
              </td>
              <td>{new Date(user.created_at).toLocaleDateString()}</td>
              <td className="action-buttons">
                <button
                  className="btn btn-success btn-sm"
                  onClick={() => handleApprove(user.id)}
                  disabled={approve.isPending}
                >
                  Approve
                </button>
                <button
                  className="btn btn-danger btn-sm"
                  onClick={() => handleDecline(user.id)}
                  disabled={decline.isPending}
                >
                  Decline
                </button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
