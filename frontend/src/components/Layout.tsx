import { ReactNode, useState } from 'react'
import { Link, useLocation } from 'react-router-dom'
import { Shield, FileText, Key, Play, FolderOpen, Home, AlertTriangle, Menu, X, Settings, ChevronDown, ChevronRight } from 'lucide-react'
import UserDropdown from './UserDropdown'

interface LayoutProps {
  children: ReactNode
}

export default function Layout({ children }: LayoutProps) {
  const location = useLocation()
  const [sidebarOpen, setSidebarOpen] = useState(false)

  // Track if Findings submenu is expanded
  const [findingsExpanded, setFindingsExpanded] = useState(
    location.pathname === '/results' || location.pathname === '/vulnerabilities'
  )

  // Track if Config submenu is expanded
  const [configExpanded, setConfigExpanded] = useState(
    location.pathname === '/templates' || location.pathname === '/api-config'
  )

  const toggleFindings = (e: React.MouseEvent) => {
    e.preventDefault()
    setFindingsExpanded(!findingsExpanded)
  }

  const toggleConfig = (e: React.MouseEvent) => {
    e.preventDefault()
    setConfigExpanded(!configExpanded)
  }

  return (
    <div className="min-h-screen bg-slate-900">
      {/* Header */}
      <header className="bg-slate-800 border-b border-slate-700 sticky top-0 z-[90]">
        <div className="w-full">
          <div className="flex items-center h-16 pl-2 sm:pl-4 md:pl-6 lg:pl-8 pr-2 sm:pr-4 md:pr-6 lg:pr-8 relative">
            {/* Mobile menu button */}
            <button
              onClick={(e) => {
                e.preventDefault()
                e.stopPropagation()
                setSidebarOpen(!sidebarOpen)
              }}
              className="lg:hidden p-2 rounded-lg text-slate-300 hover:bg-slate-700 hover:text-white active:bg-slate-600 mr-2 z-[100] relative touch-manipulation cursor-pointer"
              aria-label="Toggle menu"
              type="button"
            >
              {sidebarOpen ? <X className="h-6 w-6 pointer-events-none" /> : <Menu className="h-6 w-6 pointer-events-none" />}
            </button>

            <div className="flex items-center space-x-2 sm:space-x-3 flex-1 min-w-0">
              <Shield className="h-6 w-6 sm:h-7 sm:w-7 text-primary-500 flex-shrink-0" />
              <h1 className="text-lg sm:text-xl font-semibold tracking-tight text-white truncate">Hades Security</h1>
            </div>

            {/* User menu */}
            <div className="flex items-center gap-3">
              <UserDropdown />
            </div>
          </div>
        </div>
      </header>

      <div className="flex flex-col min-h-[calc(100vh-4rem)]">
        <div className="flex flex-1 relative">
          {/* Mobile Sidebar Overlay */}
          {sidebarOpen && (
            <div
              className="fixed inset-0 bg-black bg-opacity-50 z-[55] lg:hidden"
              onClick={() => setSidebarOpen(false)}
            />
          )}

          {/* Sidebar - Fixed position for desktop */}
          <aside
            className={`fixed top-16 left-0 z-[60] w-64 h-[calc(100vh-4rem)] bg-slate-800 border-r border-slate-700 transform transition-transform duration-300 ease-in-out lg:translate-x-0 ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'
              }`}
          >
            <nav className="p-4 space-y-1.5 h-full overflow-y-auto">
              <Link
                to="/"
                onClick={() => setSidebarOpen(false)}
                className={`flex items-center space-x-3 px-4 py-2.5 rounded-lg transition-colors ${location.pathname === '/'
                    ? 'bg-primary-600 text-white font-medium'
                    : 'text-slate-300 hover:bg-slate-700 hover:text-white'
                  }`}
              >
                <Home className="h-5 w-5 flex-shrink-0" />
                <span className="text-sm">Dashboard</span>
              </Link>

              <Link
                to="/scan"
                onClick={() => setSidebarOpen(false)}
                className={`flex items-center space-x-3 px-4 py-2.5 rounded-lg transition-colors ${location.pathname === '/scan'
                    ? 'bg-primary-600 text-white font-medium'
                    : 'text-slate-300 hover:bg-slate-700 hover:text-white'
                  }`}
              >
                <Play className="h-5 w-5 flex-shrink-0" />
                <span className="text-sm">Start Scan</span>
              </Link>

              {/* Combined Config Navigation (Collapsible Parent) */}
              <div className="space-y-1">
                <button
                  onClick={toggleConfig}
                  className={`w-full flex items-center justify-between px-4 py-2.5 rounded-lg transition-colors text-slate-300 hover:bg-slate-700 hover:text-white ${
                    location.pathname === '/templates' || location.pathname === '/api-config'
                      ? 'bg-slate-700/50 text-white font-medium'
                      : ''
                  }`}
                >
                  <div className="flex items-center space-x-3">
                    <Key className="h-5 w-5 flex-shrink-0" />
                    <span className="text-sm">Config</span>
                  </div>
                  {configExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                </button>

                {configExpanded && (
                  <div className="pl-6 space-y-1 animate-in slide-in-from-top-1 duration-150">
                    <Link
                      to="/templates"
                      onClick={() => setSidebarOpen(false)}
                      className={`flex items-center space-x-3 px-4 py-2 rounded-lg transition-colors ${
                        location.pathname === '/templates'
                          ? 'bg-primary-600 text-white font-medium'
                          : 'text-slate-400 hover:bg-slate-750 hover:text-white'
                      }`}
                    >
                      <FileText className="h-4 w-4 flex-shrink-0" />
                      <span className="text-xs">Templates</span>
                    </Link>
                    <Link
                      to="/api-config"
                      onClick={() => setSidebarOpen(false)}
                      className={`flex items-center space-x-3 px-4 py-2 rounded-lg transition-colors ${
                        location.pathname === '/api-config'
                          ? 'bg-primary-600 text-white font-medium'
                          : 'text-slate-400 hover:bg-slate-750 hover:text-white'
                      }`}
                    >
                      <Key className="h-4 w-4 flex-shrink-0" />
                      <span className="text-xs">API Keys</span>
                    </Link>
                  </div>
                )}
              </div>

              {/* Combined Findings Navigation (Collapsible Parent) */}
              <div className="space-y-1">
                <button
                  onClick={toggleFindings}
                  className={`w-full flex items-center justify-between px-4 py-2.5 rounded-lg transition-colors text-slate-300 hover:bg-slate-700 hover:text-white ${
                    location.pathname === '/results' || location.pathname === '/vulnerabilities'
                      ? 'bg-slate-700/50 text-white font-medium'
                      : ''
                  }`}
                >
                  <div className="flex items-center space-x-3">
                    <FolderOpen className="h-5 w-5 flex-shrink-0" />
                    <span className="text-sm">Findings</span>
                  </div>
                  {findingsExpanded ? <ChevronDown className="h-4 w-4" /> : <ChevronRight className="h-4 w-4" />}
                </button>

                {findingsExpanded && (
                  <div className="pl-6 space-y-1 animate-in slide-in-from-top-1 duration-150">
                    <Link
                      to="/results"
                      onClick={() => setSidebarOpen(false)}
                      className={`flex items-center space-x-3 px-4 py-2 rounded-lg transition-colors ${
                        location.pathname === '/results'
                          ? 'bg-primary-600 text-white font-medium'
                          : 'text-slate-400 hover:bg-slate-750 hover:text-white'
                      }`}
                    >
                      <FolderOpen className="h-4 w-4 flex-shrink-0" />
                      <span className="text-xs">Scan History</span>
                    </Link>
                    <Link
                      to="/vulnerabilities"
                      onClick={() => setSidebarOpen(false)}
                      className={`flex items-center space-x-3 px-4 py-2 rounded-lg transition-colors ${
                        location.pathname === '/vulnerabilities'
                          ? 'bg-primary-600 text-white font-medium'
                          : 'text-slate-400 hover:bg-slate-750 hover:text-white'
                      }`}
                    >
                      <AlertTriangle className="h-4 w-4 flex-shrink-0" />
                      <span className="text-xs">Vulnerability List</span>
                    </Link>
                  </div>
                )}
              </div>

              <Link
                to="/settings"
                onClick={() => setSidebarOpen(false)}
                className={`flex items-center space-x-3 px-4 py-2.5 rounded-lg transition-colors ${location.pathname === '/settings'
                    ? 'bg-primary-600 text-white font-medium'
                    : 'text-slate-300 hover:bg-slate-700 hover:text-white'
                  }`}
              >
                <Settings className="h-5 w-5 flex-shrink-0" />
                <span className="text-sm">Settings</span>
              </Link>
            </nav>
          </aside>

          {/* Main Content - left margin on desktop */}
          <main className="flex-1 p-4 sm:p-6 md:p-6 w-full min-w-0 lg:ml-64">
            {children}
          </main>
        </div>

        {/* Footer */}
        <footer className="bg-slate-800 border-t border-slate-700 py-4 lg:ml-64">
          <div className="w-full text-center px-4">
            <p className="text-xs sm:text-sm text-slate-400">
              © {new Date().getFullYear()} <span className="text-primary-500 font-semibold">Hades Security</span>. All rights reserved.
            </p>
          </div>
        </footer>
      </div>
    </div>
  )
}
