import { useRef, useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { toast } from 'sonner'
import { authApi, usersApi } from '@/api'
import { useAuthStore } from '@/store/authStore'
import { Navbar } from '@/components/common/Navbar'

// ─── Types ────────────────────────────────────────────────────────────────────

interface TOTPSetup {
  secret: string
  qr_code_url: string
  provisioning_uri: string
}

// ─── Avatar Section ───────────────────────────────────────────────────────────

function AvatarSection() {
  const { user, setUser } = useAuthStore()
  const fileRef = useRef<HTMLInputElement>(null)
  const [uploading, setUploading] = useState(false)

  const handleFile = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    try {
      const updated = await usersApi.uploadAvatar(file)
      setUser(updated)
      toast.success('Avatar updated')
    } catch {
      toast.error('Failed to upload avatar')
    } finally {
      setUploading(false)
      if (fileRef.current) fileRef.current.value = ''
    }
  }

  const handleRemove = async () => {
    setUploading(true)
    try {
      const updated = await usersApi.deleteAvatar()
      setUser(updated)
      toast.success('Avatar removed')
    } catch {
      toast.error('Failed to remove avatar')
    } finally {
      setUploading(false)
    }
  }

  return (
    <div className="profile-section">
      <h3 className="profile-section-title">Profile Picture</h3>
      <div className="avatar-row">
        <div className="avatar-preview">
          {user?.avatar_url ? (
            <img src={user.avatar_url} alt="Avatar" className="avatar-img" />
          ) : (
            <div className="avatar-placeholder">
              {user?.full_name?.charAt(0).toUpperCase() ?? '?'}
            </div>
          )}
        </div>
        <div className="avatar-actions">
          <input
            ref={fileRef}
            type="file"
            accept="image/jpeg,image/png,image/webp,image/gif"
            style={{ display: 'none' }}
            onChange={handleFile}
          />
          <button
            className="btn btn-secondary btn-sm"
            onClick={() => fileRef.current?.click()}
            disabled={uploading}
          >
            {uploading ? 'Uploading…' : 'Upload Photo'}
          </button>
          {user?.avatar_url && (
            <button
              className="btn btn-ghost btn-sm"
              onClick={handleRemove}
              disabled={uploading}
            >
              Remove
            </button>
          )}
          <p className="profile-hint">JPEG, PNG, WebP or GIF · max 2 MB</p>
        </div>
      </div>
    </div>
  )
}

// ─── Profile Info Section ────────────────────────────────────────────────────

function ProfileInfoSection() {
  const { user, setUser } = useAuthStore()
  const [name, setName] = useState(user?.full_name ?? '')
  const [editing, setEditing] = useState(false)

  const mutation = useMutation({
    mutationFn: () => usersApi.update(user!.id, { full_name: name }),
    onSuccess: (updated) => {
      setUser(updated)
      setEditing(false)
      toast.success('Name updated')
    },
    onError: () => toast.error('Failed to update name'),
  })

  return (
    <div className="profile-section">
      <h3 className="profile-section-title">Account Info</h3>
      <div className="form-group">
        <label>Email</label>
        <input value={user?.email ?? ''} disabled className="profile-input-disabled" />
      </div>
      <div className="form-group" style={{ marginTop: '0.75rem' }}>
        <label>Full Name</label>
        <div className="profile-edit-row">
          <input
            value={name}
            onChange={(e) => { setName(e.target.value); setEditing(true) }}
            style={{ flex: 1 }}
          />
          {editing && (
            <>
              <button
                className="btn btn-primary btn-sm"
                onClick={() => mutation.mutate()}
                disabled={mutation.isPending || !name.trim()}
              >
                Save
              </button>
              <button
                className="btn btn-ghost btn-sm"
                onClick={() => { setName(user?.full_name ?? ''); setEditing(false) }}
              >
                Cancel
              </button>
            </>
          )}
        </div>
      </div>
      {user?.organization_name && (
        <div className="profile-meta">
          Organisation: <strong>{user.org_abbrev} {user.organization_name}</strong>
        </div>
      )}
    </div>
  )
}

// ─── Password Section ────────────────────────────────────────────────────────

function PasswordSection() {
  const { user } = useAuthStore()
  const [next, setNext] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')

  const mutation = useMutation({
    mutationFn: () => usersApi.update(user!.id, { password: next }),
    onSuccess: () => {
      setNext(''); setConfirm('')
      setError('')
      toast.success('Password changed')
    },
    onError: () => toast.error('Failed to change password'),
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    if (next.length < 8) { setError('Password must be at least 8 characters'); return }
    if (next !== confirm) { setError('Passwords do not match'); return }
    mutation.mutate()
  }

  return (
    <div className="profile-section">
      <h3 className="profile-section-title">Change Password</h3>
      <form onSubmit={handleSubmit} className="profile-form">
        <div className="form-group">
          <label>New Password</label>
          <input type="password" value={next} onChange={(e) => setNext(e.target.value)} placeholder="Min. 8 characters" />
        </div>
        <div className="form-group">
          <label>Confirm New Password</label>
          <input type="password" value={confirm} onChange={(e) => setConfirm(e.target.value)} />
        </div>
        {error && <p className="error">{error}</p>}
        <div className="form-actions">
          <button type="submit" className="btn btn-primary btn-sm" disabled={mutation.isPending || !next || !confirm}>
            {mutation.isPending ? 'Saving…' : 'Change Password'}
          </button>
        </div>
      </form>
    </div>
  )
}

// ─── 2FA Section ─────────────────────────────────────────────────────────────

function TwoFactorSection() {
  const { user, setUser } = useAuthStore()
  const [setup, setSetup] = useState<TOTPSetup | null>(null)
  const [verifyCode, setVerifyCode] = useState('')
  const [disableCode, setDisableCode] = useState('')
  const [showDisable, setShowDisable] = useState(false)
  const queryClient = useQueryClient()

  const startSetup = useMutation({
    mutationFn: authApi.setupTotp,
    onSuccess: (data) => setSetup(data),
    onError: () => toast.error('Failed to start 2FA setup'),
  })

  const verifyMutation = useMutation({
    mutationFn: () => authApi.verifyTotp(verifyCode),
    onSuccess: async () => {
      const updated = await authApi.me()
      setUser(updated)
      queryClient.invalidateQueries({ queryKey: ['me'] })
      setSetup(null)
      setVerifyCode('')
      toast.success('Two-factor authentication enabled')
    },
    onError: () => toast.error('Invalid code — please try again'),
  })

  const disableMutation = useMutation({
    mutationFn: () => authApi.disableTotp(disableCode),
    onSuccess: async () => {
      const updated = await authApi.me()
      setUser(updated)
      queryClient.invalidateQueries({ queryKey: ['me'] })
      setDisableCode('')
      setShowDisable(false)
      toast.success('Two-factor authentication disabled')
    },
    onError: () => toast.error('Invalid code — please try again'),
  })

  if (user?.totp_enabled) {
    return (
      <div className="profile-section">
        <h3 className="profile-section-title">Two-Factor Authentication</h3>
        <div className="totp-status totp-enabled">
          <span>🔒 2FA is currently <strong>enabled</strong></span>
        </div>
        {!showDisable ? (
          <button className="btn btn-danger btn-sm" style={{ marginTop: '0.75rem' }} onClick={() => setShowDisable(true)}>
            Disable 2FA
          </button>
        ) : (
          <div className="totp-disable-form" style={{ marginTop: '0.75rem' }}>
            <div className="form-group">
              <label>Enter your current authenticator code to confirm</label>
              <input
                value={disableCode}
                onChange={(e) => setDisableCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
                placeholder="6-digit code"
                maxLength={6}
                style={{ letterSpacing: '0.2em', fontFamily: 'monospace' }}
              />
            </div>
            <div className="form-actions" style={{ marginTop: '0.5rem' }}>
              <button
                className="btn btn-danger btn-sm"
                onClick={() => disableMutation.mutate()}
                disabled={disableMutation.isPending || disableCode.length !== 6}
              >
                {disableMutation.isPending ? 'Disabling…' : 'Confirm Disable'}
              </button>
              <button className="btn btn-ghost btn-sm" onClick={() => { setShowDisable(false); setDisableCode('') }}>
                Cancel
              </button>
            </div>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="profile-section">
      <h3 className="profile-section-title">Two-Factor Authentication</h3>
      <div className="totp-status totp-disabled">
        <span>🔓 2FA is currently <strong>disabled</strong></span>
      </div>

      {!setup ? (
        <button
          className="btn btn-primary btn-sm"
          style={{ marginTop: '0.75rem' }}
          onClick={() => startSetup.mutate()}
          disabled={startSetup.isPending}
        >
          {startSetup.isPending ? 'Setting up…' : 'Enable 2FA'}
        </button>
      ) : (
        <div className="totp-setup" style={{ marginTop: '1rem' }}>
          <p className="profile-hint" style={{ marginBottom: '0.75rem' }}>
            Scan the QR code with your authenticator app (e.g. Google Authenticator, Authy),
            then enter the 6-digit code below to confirm.
          </p>
          <div className="totp-qr-wrap">
            <img src={setup.qr_code_url} alt="TOTP QR code" className="totp-qr" />
          </div>
          <details className="totp-manual" style={{ marginTop: '0.5rem', marginBottom: '0.75rem' }}>
            <summary style={{ fontSize: '0.8125rem', cursor: 'pointer', color: 'var(--color-text-muted)' }}>
              Enter key manually
            </summary>
            <code className="totp-secret">{setup.secret}</code>
          </details>
          <div className="form-group">
            <label>Verification Code</label>
            <input
              value={verifyCode}
              onChange={(e) => setVerifyCode(e.target.value.replace(/\D/g, '').slice(0, 6))}
              placeholder="6-digit code"
              maxLength={6}
              style={{ letterSpacing: '0.2em', fontFamily: 'monospace' }}
            />
          </div>
          <div className="form-actions" style={{ marginTop: '0.5rem' }}>
            <button
              className="btn btn-primary btn-sm"
              onClick={() => verifyMutation.mutate()}
              disabled={verifyMutation.isPending || verifyCode.length !== 6}
            >
              {verifyMutation.isPending ? 'Verifying…' : 'Verify & Enable'}
            </button>
            <button className="btn btn-ghost btn-sm" onClick={() => { setSetup(null); setVerifyCode('') }}>
              Cancel
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export function ProfilePage() {
  return (
    <div className="app-layout">
      <Navbar />
      <main className="app-main">
        <div className="profile-page">
          <h1 className="profile-title">My Profile</h1>
          <AvatarSection />
          <ProfileInfoSection />
          <PasswordSection />
          <TwoFactorSection />
        </div>
      </main>
    </div>
  )
}
