import { useState } from 'react'
import { toast } from 'sonner'
import { usersApi, authApi } from '@/api'
import { useAuthStore } from '@/store/authStore'

export function ForcePasswordChangeModal() {
  const { user, setUser } = useAuthStore()
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [isLoading, setIsLoading] = useState(false)

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (newPassword.length < 8) {
      toast.error('Password must be at least 8 characters')
      return
    }
    if (newPassword !== confirmPassword) {
      toast.error('Passwords do not match')
      return
    }
    if (!user) return
    setIsLoading(true)
    try {
      await usersApi.update(user.id, { password: newPassword })
      const refreshed = await authApi.me()
      setUser(refreshed)
      toast.success('Password changed successfully')
    } catch {
      toast.error('Failed to change password')
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="modal-overlay force-pw-overlay">
      <div className="modal force-pw-modal" role="dialog" aria-modal aria-label="Change Password Required">
        <div className="modal-header">
          <h2>Change Password Required</h2>
        </div>
        <p className="force-pw-notice">
          Your account requires a password change before you can continue.
          Please set a new password below.
        </p>
        <form onSubmit={handleSubmit} className="auth-form">
          <div className="form-group">
            <label htmlFor="new-password">New Password</label>
            <input
              id="new-password"
              type="password"
              value={newPassword}
              onChange={(e) => setNewPassword(e.target.value)}
              placeholder="Min. 8 characters"
              autoFocus
              required
            />
          </div>
          <div className="form-group">
            <label htmlFor="confirm-password">Confirm Password</label>
            <input
              id="confirm-password"
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
              placeholder="Repeat new password"
              required
            />
          </div>
          <button
            type="submit"
            disabled={isLoading || !newPassword || !confirmPassword}
            className="btn btn-primary btn-full"
          >
            {isLoading ? 'Saving…' : 'Change Password'}
          </button>
        </form>
      </div>
    </div>
  )
}
