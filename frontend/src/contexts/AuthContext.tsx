import { createContext, useContext, useState, useEffect, ReactNode } from 'react'
import { authAPI } from '../api/client'

interface User {
  email: string
  name: string
  username?: string
  profile_image?: string
  username_changes?: Array<{
    old_username: string
    new_username: string
    timestamp: string
  }>
}

interface AuthContextType {
  user: User | null
  token: string | null
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, name: string) => Promise<void>
  logout: () => void
  isAuthenticated: boolean
  loading: boolean
}

const AuthContext = createContext<AuthContextType | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    // Check for stored token on mount
    const loadUser = async () => {
      const storedToken = localStorage.getItem('token')
      const storedUser = localStorage.getItem('user')
      
      if (storedToken && storedUser) {
        try {
          setToken(storedToken)
          const userData = JSON.parse(storedUser)
          setUser(userData)
          
          // Refresh user data from server
          try {
            const response = await authAPI.getMe()
            const updatedUser = { ...userData, ...response.data }
            setUser(updatedUser)
            localStorage.setItem('user', JSON.stringify(updatedUser))
          } catch (e) {
            // If token is invalid, clear storage
            localStorage.removeItem('token')
            localStorage.removeItem('user')
            setToken(null)
            setUser(null)
          }
        } catch (e) {
          localStorage.removeItem('token')
          localStorage.removeItem('user')
        }
      }
      setLoading(false)
    }
    
    loadUser()
  }, [])

  const login = async (email: string, password: string) => {
    try {
      const response = await authAPI.login(email, password)
      const { access_token, user: userData } = response.data
      
      localStorage.setItem('token', access_token)
      localStorage.setItem('user', JSON.stringify(userData))
      setToken(access_token)
      setUser(userData)
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Login failed')
    }
  }

  const register = async (email: string, password: string, name: string) => {
    try {
      const response = await authAPI.register(email, password, name)
      const { access_token, user: userData } = response.data
      
      localStorage.setItem('token', access_token)
      localStorage.setItem('user', JSON.stringify(userData))
      setToken(access_token)
      setUser(userData)
    } catch (error: any) {
      throw new Error(error.response?.data?.detail || 'Registration failed')
    }
  }

  const logout = () => {
    localStorage.removeItem('token')
    localStorage.removeItem('user')
    setToken(null)
    setUser(null)
  }

  return (
    <AuthContext.Provider
      value={{
        user,
        token,
        login,
        register,
        logout,
        isAuthenticated: !!token && !!user,
        loading,
      }}
    >
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider')
  }
  return context
}

