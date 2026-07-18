import { useState, useEffect } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { authAPI } from '../api/client'
import { User, Camera, Key, Mail, Save, AlertCircle, CheckCircle } from 'lucide-react'

export default function Profile() {
  const { user } = useAuth()
  const [searchParams, setSearchParams] = useSearchParams()
  const tab = searchParams.get('tab') || 'profile'
  
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')
  
  // Profile settings
  const [username, setUsername] = useState('')
  const [profileImage, setProfileImage] = useState<string | null>(null)
  const [imageFile, setImageFile] = useState<File | null>(null)
  const [changesRemaining, setChangesRemaining] = useState(2)
  
  // Password change
  const [currentPassword, setCurrentPassword] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  
  // Email change
  const [newEmail, setNewEmail] = useState('')
  const [emailPassword, setEmailPassword] = useState('')

  useEffect(() => {
    if (user) {
      setUsername(user.username || user.name || '')
      if (user.profile_image) {
        // Use API URL instead of data URL for security
        setProfileImage(authAPI.getProfileImage(user.profile_image))
      }
      // Calculate changes remaining
      if (user.username_changes) {
        const sevenDaysAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000)
        const recentChanges = user.username_changes.filter((change: any) => 
          new Date(change.timestamp || change.changed_at) > sevenDaysAgo
        )
        setChangesRemaining(Math.max(0, 2 - recentChanges.length))
      }
    }
  }, [user])
  
  // Cleanup: Revoke blob URLs on unmount
  useEffect(() => {
    return () => {
      if (profileImage && profileImage.startsWith('blob:')) {
        URL.revokeObjectURL(profileImage)
      }
    }
  }, [profileImage])

  const handleImageChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (!file) return

    // Security: Validate file type
    const allowedTypes = ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
    if (!allowedTypes.includes(file.type)) {
      setError('Only JPEG, PNG, GIF, and WebP images are allowed')
      return
    }

    // Security: Explicitly block SVG
    if (file.type === 'image/svg+xml' || file.name.toLowerCase().endsWith('.svg')) {
      setError('SVG files are not allowed for security reasons')
      return
    }

    // Security: Validate file extension matches content type
    const validExtensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
    const fileExt = file.name.toLowerCase().substring(file.name.lastIndexOf('.'))
    if (!validExtensions.includes(fileExt)) {
      setError('Invalid file extension')
      return
    }

    // Validate file size (5MB)
    if (file.size > 5 * 1024 * 1024) {
      setError('Image size must be less than 5MB')
      return
    }

    if (file.size === 0) {
      setError('File is empty')
      return
    }

    // Security: Clean up previous blob URL if exists before creating new one
    if (profileImage && profileImage.startsWith('blob:')) {
      URL.revokeObjectURL(profileImage)
    }

    // Security: Read file as blob URL instead of data URL to prevent XSS
    // Blob URLs are safer than data URLs and don't expose base64 content
    const blobUrl = URL.createObjectURL(file)
    setProfileImage(blobUrl)
    setImageFile(file)
    setError('')
  }

  const handleUploadImage = async () => {
    if (!imageFile) return

    setLoading(true)
    setError('')
    setSuccess('')

    try {
      await authAPI.uploadProfileImage(imageFile)
      setSuccess('Profile image uploaded successfully')
      
      // Clean up blob URL
      if (profileImage && profileImage.startsWith('blob:')) {
        URL.revokeObjectURL(profileImage)
      }
      
      setImageFile(null)
      
      // Refresh user data
      const meResponse = await authAPI.getMe()
      if (meResponse.data.profile_image) {
        // Use API URL instead of blob URL
        setProfileImage(authAPI.getProfileImage(meResponse.data.profile_image))
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to upload image')
    } finally {
      setLoading(false)
    }
  }

  const handleUpdateUsername = async (e: React.FormEvent) => {
    e.preventDefault()
    
    // Check if username actually changed
    const currentUsername = user?.username || user?.name || ''
    if (!username || username === currentUsername) {
      setError('Username is unchanged')
      return
    }
    
    setLoading(true)
    setError('')
    setSuccess('')

    // Validate username
    if (username.length < 3) {
      setError('Username must be at least 3 characters')
      setLoading(false)
      return
    }

    if (username.length > 50) {
      setError('Username must be less than 50 characters')
      setLoading(false)
      return
    }

    // XSS prevention - check for dangerous characters
    const dangerousPatterns = /[<>"';\\`$(){}%]/
    if (dangerousPatterns.test(username)) {
      setError('Username contains invalid characters')
      setLoading(false)
      return
    }

    try {
      const response = await authAPI.updateUsername(username)
      setSuccess(response.data.message)
      setChangesRemaining(response.data.changes_remaining)
      // Update local user state
      if (user) {
        const updatedUser = { ...user, username: response.data.username, name: response.data.username }
        localStorage.setItem('user', JSON.stringify(updatedUser))
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to update username')
    } finally {
      setLoading(false)
    }
  }

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSuccess('')

    if (newPassword.length < 6) {
      setError('Password must be at least 6 characters')
      return
    }

    if (newPassword !== confirmPassword) {
      setError('Passwords do not match')
      return
    }

    // Validate password for dangerous characters
    const dangerousPatterns = /[;\\`$(){}%]/
    if (dangerousPatterns.test(newPassword)) {
      setError('Password contains invalid characters')
      return
    }

    setLoading(true)
    try {
      await authAPI.changePassword(currentPassword, newPassword)
      setSuccess('Password changed successfully')
      setCurrentPassword('')
      setNewPassword('')
      setConfirmPassword('')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to change password')
    } finally {
      setLoading(false)
    }
  }

  const handleChangeEmail = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSuccess('')

    // Email validation is handled by backend
    setLoading(true)
    try {
      const response = await authAPI.changeEmail(newEmail, emailPassword)
      setSuccess('Email changed successfully!')
      // Update token and user
      localStorage.setItem('token', response.data.access_token)
      localStorage.setItem('user', JSON.stringify(response.data.user))
      // Reload page to refresh auth context
      setTimeout(() => {
        window.location.reload()
      }, 1500)
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to change email')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold text-white mb-2">Profile Settings</h1>
        <p className="text-slate-400">Manage your account settings</p>
      </div>

      {/* Tabs */}
      <div className="flex gap-2 border-b border-slate-700">
        <button
          onClick={() => setSearchParams({ tab: 'profile' })}
          className={`px-4 py-2 font-medium transition-colors ${
            tab === 'profile'
              ? 'text-primary-500 border-b-2 border-primary-500'
              : 'text-slate-400 hover:text-white'
          }`}
        >
          Profile Settings
        </button>
        <button
          onClick={() => setSearchParams({ tab: 'password' })}
          className={`px-4 py-2 font-medium transition-colors ${
            tab === 'password'
              ? 'text-primary-500 border-b-2 border-primary-500'
              : 'text-slate-400 hover:text-white'
          }`}
        >
          Reset Password
        </button>
        <button
          onClick={() => setSearchParams({ tab: 'email' })}
          className={`px-4 py-2 font-medium transition-colors ${
            tab === 'email'
              ? 'text-primary-500 border-b-2 border-primary-500'
              : 'text-slate-400 hover:text-white'
          }`}
        >
          Reset Email
        </button>
      </div>

      {/* Messages */}
      {error && (
        <div className="p-4 bg-primary-500/10 border border-primary-500/40 rounded-lg flex items-center gap-2 text-primary-400">
          <AlertCircle className="h-5 w-5" />
          <span>{error}</span>
        </div>
      )}
      {success && (
        <div className="p-4 bg-green-500/10 border border-green-500/50 rounded-lg flex items-center gap-2 text-green-400">
          <CheckCircle className="h-5 w-5" />
          <span>{success}</span>
        </div>
      )}

      {/* Profile Settings Tab */}
      {tab === 'profile' && (
        <div className="card space-y-6">
          {/* Profile Image */}
          <div>
            <label className="block text-sm font-medium text-slate-300 mb-4">
              Profile Photo
            </label>
            <div className="flex items-center gap-6">
              <div className="relative">
                {profileImage ? (
                  <img
                    src={profileImage}
                    alt="Profile"
                    className="w-24 h-24 rounded-full object-cover border-2 border-slate-700"
                    onError={() => {
                      // Security: Handle image load errors gracefully
                      setError('Failed to load image')
                      setProfileImage(null)
                    }}
                    crossOrigin="anonymous"
                  />
                ) : (
                  <div className="w-24 h-24 rounded-full bg-slate-700 flex items-center justify-center border-2 border-slate-600">
                    <User className="h-12 w-12 text-slate-400" />
                  </div>
                )}
                <label className="absolute bottom-0 right-0 p-2 bg-primary-600 rounded-full cursor-pointer hover:bg-primary-700 transition-colors">
                  <Camera className="h-4 w-4 text-white" />
                  <input
                    type="file"
                    accept="image/jpeg,image/png,image/gif,image/webp"
                    onChange={handleImageChange}
                    className="hidden"
                    // Security: Explicitly reject SVG
                    onInput={(e) => {
                      const file = (e.target as HTMLInputElement).files?.[0]
                      if (file && (file.type === 'image/svg+xml' || file.name.toLowerCase().endsWith('.svg'))) {
                        setError('SVG files are not allowed for security reasons')
                        e.preventDefault()
                      }
                    }}
                  />
                </label>
              </div>
              <div className="flex-1">
                <p className="text-sm text-slate-400 mb-2">
                  Upload a profile image (max 5MB, JPG/PNG/GIF/WebP)
                </p>
                {imageFile && (
                  <button
                    onClick={handleUploadImage}
                    disabled={loading}
                    className="px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg text-sm font-medium disabled:opacity-50"
                  >
                    {loading ? 'Uploading...' : 'Upload Image'}
                  </button>
                )}
              </div>
            </div>
          </div>

          {/* Username */}
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Username
              </label>
              <input
                type="text"
                value={username}
                onChange={(e) => {
                  setUsername(e.target.value)
                  setError('')
                }}
                minLength={3}
                maxLength={50}
                className="w-full px-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
                placeholder="Enter username"
              />
              <p className="text-xs text-slate-400 mt-1">
                You can change username {changesRemaining} more time(s) in the next 7 days
              </p>
            </div>
            <button
              onClick={(e) => {
                e.preventDefault()
                const currentUsername = user?.username || user?.name || ''
                if (!username || username.trim() === '') {
                  setError('Please enter a username')
                  return
                }
                if (username.trim() === currentUsername.trim()) {
                  setError('Username is unchanged')
                  return
                }
                handleUpdateUsername(e as any)
              }}
              disabled={loading || changesRemaining === 0 || !username || username.trim() === '' || username.trim() === (user?.username || user?.name || '').trim()}
              className="px-6 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center gap-2"
            >
              <Save className="h-4 w-4" />
              {loading ? 'Saving...' : 'Update Username'}
            </button>
          </div>
        </div>
      )}

      {/* Reset Password Tab */}
      {tab === 'password' && (
        <div className="card">
          <form onSubmit={handleChangePassword} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Current Password
              </label>
              <div className="relative">
                <Key className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-slate-400" />
                <input
                  type="password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  required
                  className="w-full pl-10 pr-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="Enter current password"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                New Password
              </label>
              <div className="relative">
                <Key className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-slate-400" />
                <input
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  required
                  minLength={6}
                  className="w-full pl-10 pr-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="Enter new password"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Confirm New Password
              </label>
              <div className="relative">
                <Key className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-slate-400" />
                <input
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  required
                  minLength={6}
                  className="w-full pl-10 pr-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="Confirm new password"
                />
              </div>
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full px-6 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              <Save className="h-4 w-4" />
              {loading ? 'Changing...' : 'Change Password'}
            </button>
          </form>
        </div>
      )}

      {/* Reset Email Tab */}
      {tab === 'email' && (
        <div className="card">
          <form onSubmit={handleChangeEmail} className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Current Email
              </label>
              <input
                type="email"
                value={user?.email || ''}
                disabled
                className="w-full px-4 py-2 bg-slate-800 border border-slate-600 rounded-lg text-slate-400 cursor-not-allowed"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                New Email
              </label>
              <div className="relative">
                <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-slate-400" />
                <input
                  type="email"
                  value={newEmail}
                  onChange={(e) => setNewEmail(e.target.value)}
                  required
                  className="w-full pl-10 pr-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="Enter new email"
                />
              </div>
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-300 mb-2">
                Current Password
              </label>
              <div className="relative">
                <Key className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-slate-400" />
                <input
                  type="password"
                  value={emailPassword}
                  onChange={(e) => setEmailPassword(e.target.value)}
                  required
                  className="w-full pl-10 pr-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-500"
                  placeholder="Enter current password"
                />
              </div>
            </div>
            <button
              type="submit"
              disabled={loading}
              className="w-full px-6 py-2 bg-primary-600 hover:bg-primary-700 text-white rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
            >
              <Save className="h-4 w-4" />
              {loading ? 'Changing...' : 'Change Email'}
            </button>
          </form>
        </div>
      )}
    </div>
  )
}

