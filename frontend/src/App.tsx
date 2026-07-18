import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider } from './contexts/AuthContext'
import Layout from './components/Layout'
import ProtectedRoute from './components/ProtectedRoute'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import Templates from './pages/Templates'
import APIConfig from './pages/APIConfig'
import ScanManager from './pages/ScanManager'
import ScanResults from './pages/ScanResults'
import Vulnerabilities from './pages/Vulnerabilities'
import Settings from './pages/Settings'
import Profile from './pages/Profile'

function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route
            path="/*"
            element={
              <ProtectedRoute>
                <Layout>
                  <Routes>
                    <Route path="/" element={<Dashboard />} />
                    <Route path="/templates" element={<Templates />} />
                    <Route path="/api-config" element={<APIConfig />} />
                    <Route path="/scan" element={<ScanManager />} />
                    <Route path="/results" element={<ScanResults />} />
                    <Route path="/vulnerabilities" element={<Vulnerabilities />} />
                    <Route path="/settings" element={<Settings />} />
                    <Route path="/profile" element={<Profile />} />
                    <Route path="*" element={<Navigate to="/" replace />} />
                  </Routes>
                </Layout>
              </ProtectedRoute>
            }
          />
        </Routes>
      </AuthProvider>
    </BrowserRouter>
  )
}

export default App

