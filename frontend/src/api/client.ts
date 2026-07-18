import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:9656/api'

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
})

// Add token to requests if available
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// Handle 401 errors (unauthorized)
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      localStorage.removeItem('user')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

// Template API
export const templateAPI = {
  list: () => apiClient.get('/templates'),
  get: (name: string) => apiClient.get(`/templates/${name}`),
  create: (name: string, content: string) => apiClient.post('/templates', { name, content }),
  update: (name: string, content: string) => apiClient.put(`/templates/${name}`, { content }),
  delete: (name: string) => apiClient.delete(`/templates/${name}`),
}

// Provider API
export const providerAPI = {
  list: () => apiClient.get('/providers'),
  save: (providers: Array<{ key: string; name: string; model: string; env_var: string; api_key_url: string; description: string; icon: string }>) =>
    apiClient.post('/providers', { providers }),
}

// Config API
export const configAPI = {
  getKeys: () => apiClient.get('/config/keys'),
  saveKeys: (configs: Array<{ provider_key: string; api_key: string }>) =>
    apiClient.post('/config/keys', configs),
  uploadProviderKeys: (providerKey: string, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('provider_key', providerKey)
    return apiClient.post('/config/provider/upload-keys', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
  },
  getProviderStatus: (providerKey: string) =>
    apiClient.get(`/config/provider/status?provider_key=${providerKey}`),
  getConfiguredProviders: () => apiClient.get('/config/providers'),
  setActiveProvider: (providerKey: string) => {
    const formData = new FormData()
    formData.append('provider_key', providerKey)
    return apiClient.post('/config/active-provider', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
  },
  testProvider: (providerKey: string, apiKey: string, model: string, apiBase?: string) =>
    apiClient.post('/config/test-provider', { provider_key: providerKey, api_key: apiKey, model, api_base: apiBase }),
}

// Docker API
export const dockerAPI = {
  getStatus: () => apiClient.get('/docker/status'),
}

// Scan API
export const scanAPI = {
  start: (request: {
    targets: string[]
    instruction?: string
    template?: string
    run_name?: string
    non_interactive?: boolean
  }) => apiClient.post('/scan/start', request),
  getResults: () => apiClient.get('/scan/results'),
  deleteResult: (resultName: string) => apiClient.delete(`/scan/results/${resultName}`),
  exportResult: (resultName: string) =>
    apiClient.get(`/scan/results/${resultName}/export`, { responseType: 'blob' }),
  exportCSV: (resultName: string) =>
    apiClient.get(`/scan/results/${resultName}/export-csv`, { responseType: 'blob' }),
  exportPDF: (resultName: string) =>
    apiClient.get(`/scan/results/${resultName}/export-pdf`, { responseType: 'blob' }),
}

// System API
export const systemAPI = {
  getInfo: () => apiClient.get('/system/info'),
  health: () => apiClient.get('/health'),
}

// Activity API
export const activityAPI = {
  getActivity: () => apiClient.get('/activity'),
}

// Vulnerabilities API
export const vulnerabilitiesAPI = {
  getVulnerabilities: () => apiClient.get('/vulnerabilities'),
}

// Settings API
export const settingsAPI = {
  getSettings: () => apiClient.get('/settings'),
  saveSettings: (settings: any) => apiClient.post('/settings', settings),
  testNotification: (data: { type: 'telegram' | 'discord' }) => apiClient.post('/settings/test-notification', data),
}

// Authentication API
export const authAPI = {
  login: (email: string, password: string) =>
    apiClient.post('/auth/login', { email, password }),
  register: (email: string, password: string, name: string) =>
    apiClient.post('/auth/register', { email, password, name }),
  resetPasswordRequest: (email: string) =>
    apiClient.post('/auth/reset-password-request', { email }),
  resetPassword: (token: string, newPassword: string) =>
    apiClient.post('/auth/reset-password', { token, new_password: newPassword }),
  getMe: () => apiClient.get('/auth/me'),
  updateUsername: (newUsername: string) =>
    apiClient.put('/auth/username', { new_username: newUsername }),
  uploadProfileImage: (file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return apiClient.post('/auth/profile-image', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    })
  },
  getProfileImage: (filename: string) => {
    const baseURL = apiClient.defaults.baseURL || 'http://localhost:9656/api'
    return `${baseURL}/auth/profile-image/${filename}`
  },
  changePassword: (currentPassword: string, newPassword: string) =>
    apiClient.post('/auth/change-password', { current_password: currentPassword, new_password: newPassword }),
  changeEmail: (newEmail: string, password: string) =>
    apiClient.post('/auth/change-email', { new_email: newEmail, password }),
}

