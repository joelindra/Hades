import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../contexts/AuthContext'
import { authAPI } from '../api/client'
import { User, Settings, Key, Mail, LogOut, ChevronDown } from 'lucide-react'

export default function UserDropdown() {
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setIsOpen(false)
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside)
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
    }
  }, [isOpen])

  const handleLogout = () => {
    logout()
    navigate('/login', { replace: true })
  }

  const profileImage = user?.profile_image 
    ? authAPI.getProfileImage(user.profile_image)
    : null

  return (
    <div className="relative" ref={dropdownRef}>
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center gap-2 p-2 rounded-lg text-slate-300 hover:bg-slate-700 hover:text-white transition-colors"
      >
        {profileImage ? (
          <img
            src={profileImage}
            alt={user?.name || user?.email}
            className="w-8 h-8 rounded-full object-cover"
          />
        ) : (
          <div className="w-8 h-8 rounded-full bg-primary-600 flex items-center justify-center">
            <User className="h-4 w-4 text-white" />
          </div>
        )}
        <span className="hidden sm:block text-sm font-medium">
          {user?.username || user?.name || user?.email}
        </span>
        <ChevronDown className={`h-4 w-4 transition-transform ${isOpen ? 'rotate-180' : ''}`} />
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-56 bg-slate-800 border border-slate-700 rounded-lg shadow-xl z-[80]">
          <div className="py-1">
            <button
              onClick={() => {
                setIsOpen(false)
                navigate('/profile')
              }}
              className="w-full flex items-center gap-3 px-4 py-2 text-sm text-slate-300 hover:bg-slate-700 hover:text-white transition-colors"
            >
              <Settings className="h-4 w-4" />
              <span>Profile Settings</span>
            </button>
            
            <button
              onClick={() => {
                setIsOpen(false)
                navigate('/profile?tab=password')
              }}
              className="w-full flex items-center gap-3 px-4 py-2 text-sm text-slate-300 hover:bg-slate-700 hover:text-white transition-colors"
            >
              <Key className="h-4 w-4" />
              <span>Reset Password</span>
            </button>
            
            <button
              onClick={() => {
                setIsOpen(false)
                navigate('/profile?tab=email')
              }}
              className="w-full flex items-center gap-3 px-4 py-2 text-sm text-slate-300 hover:bg-slate-700 hover:text-white transition-colors"
            >
              <Mail className="h-4 w-4" />
              <span>Reset Email</span>
            </button>
            
            <div className="border-t border-slate-700 my-1"></div>
            
            <button
              onClick={handleLogout}
              className="w-full flex items-center gap-3 px-4 py-2 text-sm text-primary-400 hover:bg-slate-700 hover:text-red-300 transition-colors"
            >
              <LogOut className="h-4 w-4" />
              <span>Logout</span>
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

