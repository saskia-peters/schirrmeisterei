import { useState } from 'react'
import { toast } from 'sonner'
import {
  useUsers,
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
} from '@/hooks/useApi'
import { useAuthStore } from '@/store/authStore'
import type { ConfigItem, ConfigItemType, User, UserGroup } from '@/types'

type AdminTab = ConfigItemType | 'user-roles' | 'age-thresholds' | 'users'

const BASE_TABS: { type: AdminTab; label: string }[] = [
  { type: 'priority', label: 'Priorities' },
  { type: 'category', label: 'Categories' },
  { type: 'group', label: 'Affected Groups' },
  { type: 'user-roles', label: 'User Roles' },
  { type: 'age-thresholds', label: 'Age Thresholds' },
]

interface AdminPanelProps {
  onClose: () => void
}

export function AdminPanel({ onClose }: AdminPanelProps) {
  const { user } = useAuthStore()
  const [activeTab, setActiveTab] = useState<AdminTab>('priority')
  const isSuperuser = user?.is_superuser ?? false
  const isAdmin = user?.groups?.includes('admin') ?? false

  const tabs = [
    ...BASE_TABS,
    ...(isAdmin || isSuperuser ? [{ type: 'users' as AdminTab, label: 'Users' }] : []),
  ]

  return (
    <div className="modal-overlay" onClick={(e) => e.target === e.currentTarget && onClose()}>
      <div className="modal admin-panel" role="dialog" aria-modal aria-label="Admin Panel">
        <div className="modal-header">
          <h2>Administration</h2>
          <button className="modal-close" onClick={onClose} aria-label="Close">✕</button>
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
          {activeTab === 'users'
            ? <UserOverview />
            : activeTab === 'user-roles'
            ? <UserRoleAdmin isSuperuser={isSuperuser} />
            : activeTab === 'age-thresholds'
            ? <AgeThresholdsAdmin isSuperuser={isSuperuser} />
            : <ConfigItemList type={activeTab as ConfigItemType} isSuperuser={isSuperuser} />}
        </div>
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

function UserRoleAdmin({ isSuperuser }: { isSuperuser: boolean }) {
  const { data: users = [] } = useUsers(isSuperuser)
  const { data: groups = [] } = useUserGroups(isSuperuser)

  const createGroup = useCreateUserGroup()
  const updateGroup = useUpdateUserGroup()
  const deleteGroup = useDeleteUserGroup()
  const setUserGroups = useSetUserGroups()

  const [newGroupName, setNewGroupName] = useState('')
  const [editingGroupId, setEditingGroupId] = useState<string | null>(null)
  const [editingGroupName, setEditingGroupName] = useState('')

  if (!isSuperuser) {
    return <p className="admin-loading">Only admins can manage user roles.</p>
  }

  const coreGroups = new Set(['helfende', 'schirrmeister', 'admin'])
  const sortedGroups = [...groups].sort((a, b) => a.name.localeCompare(b.name))

  const handleCreateGroup = async () => {
    const name = newGroupName.trim().toLowerCase()
    if (!name) return
    try {
      await createGroup.mutateAsync({ name })
      setNewGroupName('')
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
                return (
                  <td key={`${u.id}-${group.id}`}>
                    <input
                      type="checkbox"
                      checked={checked || isHelfende}
                      disabled={isHelfende}
                      onChange={(e) => handleToggleUserGroup(u, group.name, e.target.checked)}
                    />
                  </td>
                )
              })}
            </tr>
          ))}
        </tbody>
      </table>
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
  const { data: users = [], isLoading } = useAdminUsers()

  if (isLoading) return <p className="admin-loading">Loading…</p>

  return (
    <div className="user-overview">
      <table className="admin-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Email</th>
            <th>Roles</th>
            <th>Superuser</th>
            <th>Active</th>
          </tr>
        </thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.id}>
              <td>{u.full_name}</td>
              <td>{u.email}</td>
              <td>
                <div className="role-badges">
                  {u.groups.map((g) => (
                    <span key={g} className="role-badge">{g}</span>
                  ))}
                </div>
              </td>
              <td>{u.is_superuser ? '✓' : ''}</td>
              <td>{u.is_active ? '✓' : '✗'}</td>
            </tr>
          ))}
          {users.length === 0 && (
            <tr>
              <td colSpan={5} className="admin-empty">No users found.</td>
            </tr>
          )}
        </tbody>
      </table>
    </div>
  )
}
