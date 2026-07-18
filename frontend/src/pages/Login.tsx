import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { authAPI } from '../api/client'
import { Shield, Mail, Lock, User, ArrowRight, ArrowLeft, KeyRound } from 'lucide-react'

type Mode = 'login' | 'register' | 'reset-password'

export default function Login() {
  const navigate = useNavigate()
  const { login, register, isAuthenticated } = useAuth()
  const [mode, setMode] = useState<Mode>('login')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [success, setSuccess] = useState('')

  // Login form
  const [loginEmail, setLoginEmail] = useState('')
  const [loginPassword, setLoginPassword] = useState('')

  // Register form
  const [regName, setRegName] = useState('')
  const [regEmail, setRegEmail] = useState('')
  const [regPassword, setRegPassword] = useState('')
  const [regConfirmPassword, setRegConfirmPassword] = useState('')

  // Reset password form
  const [resetEmail, setResetEmail] = useState('')
  const [resetToken, setResetToken] = useState('')
  const [resetNewPassword, setResetNewPassword] = useState('')
  const [resetStep, setResetStep] = useState<'request' | 'reset'>('request')


  // Redirect if already authenticated
  if (isAuthenticated) {
    navigate('/', { replace: true })
    return null
  }

  const handleLogin = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    setLoading(true)

    try {
      await login(loginEmail, loginPassword)
      navigate('/', { replace: true })
    } catch (err: any) {
      setError(err.message || 'Login failed')
    } finally {
      setLoading(false)
    }
  }

  const handleRegister = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSuccess('')

    if (regPassword !== regConfirmPassword) {
      setError('Passwords do not match')
      return
    }

    if (regPassword.length < 6) {
      setError('Password must be at least 6 characters')
      return
    }

    setLoading(true)
    try {
      await register(regEmail, regPassword, regName)
      navigate('/', { replace: true })
    } catch (err: any) {
      setError(err.message || 'Registration failed')
    } finally {
      setLoading(false)
    }
  }

  const handleResetPasswordRequest = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSuccess('')
    setLoading(true)

    try {
      const response = await authAPI.resetPasswordRequest(resetEmail)
      setSuccess('Reset token generated. Check your response or email.')
      setResetToken(response.data.token || '')
      setResetStep('reset')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to request password reset')
    } finally {
      setLoading(false)
    }
  }

  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setSuccess('')

    if (resetNewPassword.length < 6) {
      setError('Password must be at least 6 characters')
      return
    }

    setLoading(true)
    try {
      await authAPI.resetPassword(resetToken, resetNewPassword)
      setSuccess('Password reset successfully! You can now login.')
      setMode('login')
      setResetStep('request')
      setResetToken('')
      setResetNewPassword('')
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Failed to reset password')
    } finally {
      setLoading(false)
    }
  }


  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-900 via-slate-800 to-slate-900 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo/Header */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-primary-600 rounded-full mb-4">
            <Shield className="h-8 w-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-white mb-2">Hades Security</h1>
          <p className="text-slate-400">Security Testing Framework</p>
        </div>

        {/* Mode Tabs */}
        <div className="bg-slate-800 rounded-lg p-1 mb-6 flex gap-1">
          <button
            onClick={() => {
              setMode('login')
              setError('')
              setSuccess('')
            }}
            className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
              mode === 'login'
                ? 'bg-primary-600 text-white'
                : 'text-slate-300 hover:text-white hover:bg-slate-700'
            }`}
          >
            Login
          </button>
          <button
            onClick={() => {
              setMode('register')
              setError('')
              setSuccess('')
            }}
            className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
              mode === 'register'
                ? 'bg-primary-600 text-white'
                : 'text-slate-300 hover:text-white hover:bg-slate-700'
            }`}
          >
            Register
          </button>
          <button
            onClick={() => {
              setMode('reset-password')
              setError('')
              setSuccess('')
              setResetStep('request')
            }}
            className={`flex-1 py-2 px-4 rounded-md text-sm font-medium transition-colors ${
              mode === 'reset-password'
                ? 'bg-primary-600 text-white'
                : 'text-slate-300 hover:text-white hover:bg-slate-700'
            }`}
          >
            Reset Password
          </button>
        </div>

        {/* Card */}
        <div className="bg-slate-800 rounded-lg shadow-xl p-6 border border-slate-700">
          {/* Error/Success Messages */}
          {error && (
            <div className="mb-4 p-3 bg-rose-500/10 border border-rose-500/25 rounded-lg text-rose-400 text-sm">
              {error}
            </div>
          )}
          {success && (
            <div className="mb-4 p-3 bg-green-500/10 border border-green-500/50 rounded-lg text-green-400 text-sm">
              {success}
            </div>
          )}

          {/* Login Form */}
          {mode === 'login' && (
            <form onSubmit={handleLogin} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Email
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-slate-400" />
                  <input
                    type="email"
                    value={loginEmail}
                    onChange={(e) => setLoginEmail(e.target.value)}
                    required
                    className="w-full pl-10 pr-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    placeholder="your@email.com"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-slate-400" />
                  <input
                    type="password"
                    value={loginPassword}
                    onChange={(e) => setLoginPassword(e.target.value)}
                    required
                    className="w-full pl-10 pr-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    placeholder="••••••••"
                  />
                </div>
              </div>
              <button
                type="submit"
                disabled={loading}
                className="w-full bg-primary-600 hover:bg-primary-700 text-white font-medium py-2 px-4 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {loading ? 'Logging in...' : 'Login'}
                {!loading && <ArrowRight className="h-4 w-4" />}
              </button>
            </form>
          )}

          {/* Register Form */}
          {mode === 'register' && (
            <form onSubmit={handleRegister} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Full Name
                </label>
                <div className="relative">
                  <User className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-slate-400" />
                  <input
                    type="text"
                    value={regName}
                    onChange={(e) => setRegName(e.target.value)}
                    required
                    className="w-full pl-10 pr-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    placeholder="John Doe"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Email
                </label>
                <div className="relative">
                  <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-slate-400" />
                  <input
                    type="email"
                    value={regEmail}
                    onChange={(e) => setRegEmail(e.target.value)}
                    required
                    className="w-full pl-10 pr-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    placeholder="your@email.com"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-slate-400" />
                  <input
                    type="password"
                    value={regPassword}
                    onChange={(e) => setRegPassword(e.target.value)}
                    required
                    minLength={6}
                    className="w-full pl-10 pr-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    placeholder="••••••••"
                  />
                </div>
              </div>
              <div>
                <label className="block text-sm font-medium text-slate-300 mb-2">
                  Confirm Password
                </label>
                <div className="relative">
                  <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-slate-400" />
                  <input
                    type="password"
                    value={regConfirmPassword}
                    onChange={(e) => setRegConfirmPassword(e.target.value)}
                    required
                    minLength={6}
                    className="w-full pl-10 pr-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                    placeholder="••••••••"
                  />
                </div>
              </div>
              <button
                type="submit"
                disabled={loading}
                className="w-full bg-primary-600 hover:bg-primary-700 text-white font-medium py-2 px-4 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {loading ? 'Registering...' : 'Register'}
                {!loading && <ArrowRight className="h-4 w-4" />}
              </button>
            </form>
          )}

          {/* Reset Password Form */}
          {mode === 'reset-password' && (
            <>
              {resetStep === 'request' ? (
                <form onSubmit={handleResetPasswordRequest} className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">
                      Email
                    </label>
                    <div className="relative">
                      <Mail className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-slate-400" />
                      <input
                        type="email"
                        value={resetEmail}
                        onChange={(e) => setResetEmail(e.target.value)}
                        required
                        className="w-full pl-10 pr-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                        placeholder="your@email.com"
                      />
                    </div>
                  </div>
                  <button
                    type="submit"
                    disabled={loading}
                    className="w-full bg-primary-600 hover:bg-primary-700 text-white font-medium py-2 px-4 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                  >
                    {loading ? 'Requesting...' : 'Request Reset Token'}
                    {!loading && <KeyRound className="h-4 w-4" />}
                  </button>
                </form>
              ) : (
                <form onSubmit={handleResetPassword} className="space-y-4">
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">
                      Reset Token
                    </label>
                    <div className="relative">
                      <KeyRound className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-slate-400" />
                      <input
                        type="text"
                        value={resetToken}
                        onChange={(e) => setResetToken(e.target.value)}
                        required
                        className="w-full pl-10 pr-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                        placeholder="Enter reset token"
                      />
                    </div>
                    <p className="text-xs text-slate-400 mt-1">
                      Token was sent in the response (in production, check your email)
                    </p>
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-slate-300 mb-2">
                      New Password
                    </label>
                    <div className="relative">
                      <Lock className="absolute left-3 top-1/2 transform -translate-y-1/2 h-5 w-5 text-slate-400" />
                      <input
                        type="password"
                        value={resetNewPassword}
                        onChange={(e) => setResetNewPassword(e.target.value)}
                        required
                        minLength={6}
                        className="w-full pl-10 pr-4 py-2 bg-slate-700 border border-slate-600 rounded-lg text-white placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
                        placeholder="••••••••"
                      />
                    </div>
                  </div>
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => {
                        setResetStep('request')
                        setResetToken('')
                        setResetNewPassword('')
                      }}
                      className="flex-1 bg-slate-700 hover:bg-slate-600 text-white font-medium py-2 px-4 rounded-lg transition-colors flex items-center justify-center gap-2"
                    >
                      <ArrowLeft className="h-4 w-4" />
                      Back
                    </button>
                    <button
                      type="submit"
                      disabled={loading}
                      className="flex-1 bg-primary-600 hover:bg-primary-700 text-white font-medium py-2 px-4 rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                    >
                      {loading ? 'Resetting...' : 'Reset Password'}
                      {!loading && <ArrowRight className="h-4 w-4" />}
                    </button>
                  </div>
                </form>
              )}
            </>
          )}

        </div>
      </div>
    </div>
  )
}

