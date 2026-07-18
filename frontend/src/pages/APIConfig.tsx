import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { providerAPI, configAPI } from '../api/client'
import { Save, Eye, EyeOff, Upload, CheckCircle, RefreshCw, Play, TestTube2, X, Plus, Trash2, Settings, HelpCircle, ChevronDown, ChevronUp } from 'lucide-react'
import { useToast } from '../context/ToastContext'

export default function APIConfig() {
  // Use provider.key as unique identifier instead of envVar
  const [apiKeys, setApiKeys] = useState<Record<string, string>>({})
  const [visibleKeys, setVisibleKeys] = useState<Record<string, boolean>>({})
  const [testingProviders, setTestingProviders] = useState<Record<string, boolean>>({})
  const queryClient = useQueryClient()
  const { showToast } = useToast()

  interface Provider {
    key: string
    name: string
    model: string
    env_var: string
    api_key_url: string
    description: string
    icon: string
    api_base?: string
  }

  interface ConfiguredProvider {
    key: string
    name: string
    model: string
    icon: string
    description: string
    is_active: boolean
    is_multiple: boolean
    key_count: number
    current_key_index: number
    api_base?: string
  }

  const { data: providers } = useQuery<Provider[]>({
    queryKey: ['providers'],
    queryFn: () => providerAPI.list().then(res => res.data.providers),
  })

  const { data: currentKeys } = useQuery<Record<string, string>>({
    queryKey: ['api-keys'],
    queryFn: () => configAPI.getKeys().then(res => res.data.keys),
  })

  interface ProviderStatus {
    has_keys: boolean
    count: number
    current_index: number
    current_key_preview?: string
    current_key_number?: number
  }

  const [providerStatuses, setProviderStatuses] = useState<Record<string, ProviderStatus>>({})

  const { data: configuredProvidersData } = useQuery<{ providers: ConfiguredProvider[], active_provider: string | null }>({
    queryKey: ['configured-providers'],
    queryFn: () => configAPI.getConfiguredProviders().then(res => res.data),
    refetchInterval: 5000, // Refresh every 5 seconds
  })

  const setActiveProviderMutation = useMutation({
    mutationFn: (providerKey: string) => configAPI.setActiveProvider(providerKey),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['configured-providers'] })
      queryClient.invalidateQueries({ queryKey: ['api-keys'] })
      showToast('Active provider updated successfully!', 'success')
    },
    onError: (error: { response?: { data?: { detail?: string } }; message: string }) => {
      showToast(`Failed to set active provider: ${error.response?.data?.detail || error.message}`, 'error')
    },
  })

  useEffect(() => {
    if (currentKeys && providers) {
      // Map envVar values to provider keys
      setApiKeys((prev) => {
        const updated = { ...prev }
        for (const provider of providers) {
          const envVar = provider.env_var
          const providerKey = provider.key
          const envValue = (currentKeys as Record<string, string>)?.[envVar] || ''

          // Only set if not already in state (user hasn't modified it)
          if (!(providerKey in updated)) {
            updated[providerKey] = envValue
          }
        }
        return updated
      })
    }
  }, [currentKeys, providers])

  const saveMutation = useMutation({
    mutationFn: (configs: Array<{ provider_key: string; api_key: string }>) =>
      configAPI.saveKeys(configs),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] })
      queryClient.invalidateQueries({ queryKey: ['configured-providers'] })
      showToast('API keys saved successfully!', 'success')
    },
  })

  const [isEditingProviders, setIsEditingProviders] = useState(false)
  const [editableProviders, setEditableProviders] = useState<Provider[]>([])
  const [guideExpanded, setGuideExpanded] = useState(false)

  const [currentPage, setCurrentPage] = useState(1)
  const pageSize = 6
  const totalPages = providers ? Math.ceil(providers.length / pageSize) : 0
  const startIndex = (currentPage - 1) * pageSize
  const paginatedProviders = providers ? providers.slice(startIndex, startIndex + pageSize) : []

  useEffect(() => {
    if (totalPages > 0 && currentPage > totalPages) {
      setCurrentPage(totalPages)
    }
  }, [totalPages, currentPage])

  const saveProvidersMutation = useMutation({
    mutationFn: (providersList: Provider[]) => {
      console.log('Sending providers to backend:', providersList);
      return providerAPI.save(providersList);
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['providers'] })
      queryClient.invalidateQueries({ queryKey: ['configured-providers'] })
      queryClient.invalidateQueries({ queryKey: ['api-keys'] })
      setIsEditingProviders(false)
      showToast('AI providers updated successfully!', 'success')
    },
    onError: (error: any) => {
      showToast(`Failed to update providers: ${error.response?.data?.detail || error.message}`, 'error')
    }
  })

  const handleSave = () => {
    if (!providers) return

    // Each provider saves its own value independently
    // For providers with the same envVar, the last non-empty value will be used in backend
    const configs = providers.map((provider: Provider) => {
      const providerKey = provider.key
      const envVar = provider.env_var

      // Check if user has modified this provider's value
      const userModified = providerKey in apiKeys
      const stateValue = apiKeys[providerKey]
      const serverValue = (currentKeys as Record<string, string>)?.[envVar] ?? ''

      // Use state value if user modified it, otherwise use server value
      const apiKey = userModified ? stateValue : serverValue

      return {
        provider_key: provider.key,
        api_key: apiKey.trim(),
      }
    })

    saveMutation.mutate(configs)
  }

  const toggleVisibility = (providerKey: string) => {
    setVisibleKeys((prev) => ({ ...prev, [providerKey]: !prev[providerKey] }))
  }

  // Fetch status for all providers
  useEffect(() => {
    if (providers) {
      providers.forEach((provider: Provider) => {
        configAPI.getProviderStatus(provider.key)
          .then(res => {
            setProviderStatuses((prev) => ({
              ...prev,
              [provider.key]: res.data
            }))
          })
          .catch(() => {
            // Ignore errors for providers without keys
          })
      })
    }
  }, [providers])

  // Auto-refresh status every 5 seconds
  useEffect(() => {
    const interval = setInterval(() => {
      if (providers) {
        providers.forEach((provider: Provider) => {
          configAPI.getProviderStatus(provider.key)
            .then(res => {
              setProviderStatuses((prev) => ({
                ...prev,
                [provider.key]: res.data
              }))
            })
            .catch(() => { })
        })
      }
    }, 5000)
    return () => clearInterval(interval)
  }, [providers])

  const uploadProviderMutation = useMutation({
    mutationFn: ({ providerKey, file }: { providerKey: string; file: File }) =>
      configAPI.uploadProviderKeys(providerKey, file),
    onSuccess: (data, variables) => {
      queryClient.invalidateQueries({ queryKey: ['api-keys'] })
      // Refresh status for this provider
      configAPI.getProviderStatus(variables.providerKey)
        .then(res => {
          setProviderStatuses((prev) => ({
            ...prev,
            [variables.providerKey]: res.data
          }))
        })
      showToast(`Successfully uploaded ${data.data.count} ${data.data.provider_name} API key(s)!`, 'success')
      // Clear file input
      const input = document.getElementById(`provider-upload-${variables.providerKey}`) as HTMLInputElement
      if (input) input.value = ''
    },
    onError: (error: { response?: { data?: { detail?: string } }; message: string }) => {
      showToast(`Failed to upload: ${error.response?.data?.detail || error.message}`, 'error')
    },
  })

  const handleFileUpload = (providerKey: string) => (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      if (!file.name.endsWith('.txt')) {
        showToast('Please upload a .txt file', 'error')
        return
      }
      uploadProviderMutation.mutate({ providerKey, file })
    }
  }

  const refetchProviderStatus = (providerKey: string) => {
    configAPI.getProviderStatus(providerKey)
      .then(res => {
        setProviderStatuses((prev) => ({
          ...prev,
          [providerKey]: res.data
        }))
      })
      .catch(() => { })
  }

  const handleTestProvider = async (provider: Provider) => {
    const providerKey = provider.key
    const apiKey = apiKeys[providerKey] || ''

    if (!apiKey || !apiKey.trim()) {
      showToast('Please enter an API key first', 'error')
      return
    }

    setTestingProviders(prev => ({ ...prev, [providerKey]: true }))

    try {
      const response = await configAPI.testProvider(providerKey, apiKey.trim(), provider.model, provider.api_base)

      if (response.data.success) {
        showToast(`✅ ${provider.name}: ${response.data.message}`, 'success')
      } else {
        showToast(`❌ ${provider.name}: ${response.data.message}`, 'error')
      }
    } catch (error: any) {
      showToast(`❌ Test failed: ${error.response?.data?.detail || error.message}`, 'error')
    } finally {
      setTestingProviders(prev => ({ ...prev, [providerKey]: false }))
    }
  }

  return (
    <div className="space-y-4 sm:space-y-6">
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold text-white mb-2 tracking-tight">API Configuration</h1>
          <p className="text-sm sm:text-base text-slate-400">Manage your AI intelligence engines</p>
        </div>

        {configuredProvidersData?.active_provider && (
          <div className="flex items-center space-x-3 bg-primary-500/10 border border-primary-500/30 px-4 py-2.5 rounded-2xl animate-fade-in shadow-xl shadow-primary-500/5">
            <div className="relative">
              <div className="absolute inset-0 bg-primary-400 rounded-full animate-ping opacity-20"></div>
              <div className="h-2.5 w-2.5 bg-primary-500 rounded-full relative z-10"></div>
            </div>
            <div>
              <span className="text-[10px] text-primary-400 uppercase font-bold leading-none block mb-0.5">Active Engine</span>
              <span className="text-sm font-bold text-white leading-none tracking-tight">
                {configuredProvidersData.providers.find(p => p.key === configuredProvidersData.active_provider)?.name}
              </span>
            </div>
          </div>
        )}
      </div>

      {/* Active Provider Selector */}
      {configuredProvidersData && configuredProvidersData.providers.length > 0 && (
        <div className="bg-slate-800/40 backdrop-blur-xl rounded-2xl p-6 border border-slate-700/50 shadow-2xl">
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-primary-500/20 rounded-lg">
                <Play className="h-6 w-6 text-primary-400 fill-current" />
              </div>
              <div>
                <h2 className="text-xl font-bold text-white tracking-tight">Active Engine</h2>
                <p className="text-xs text-slate-400">Select which AI logic to power your scans</p>
              </div>
            </div>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
            {configuredProvidersData.providers.map((provider: ConfiguredProvider) => (
              <div
                key={provider.key}
                onClick={() => !provider.is_active && setActiveProviderMutation.mutate(provider.key)}
                className={`group relative p-4 rounded-xl border-2 cursor-pointer transition-all duration-300 ${provider.is_active
                  ? 'border-primary-500 bg-primary-500/10 shadow-lg shadow-primary-500/10'
                  : 'border-slate-700 bg-slate-800/50 hover:border-slate-500 hover:bg-slate-700/50'
                  }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-2">
                      <span className="text-2xl group-hover:scale-110 transition-transform">{provider.icon}</span>
                      <div>
                        <span className="font-bold text-white text-sm block">{provider.name}</span>
                        <span className="text-[10px] text-slate-500 uppercase tracking-tighter">
                          {provider.is_multiple ? `${provider.key_count} Keys` : 'Single Key'}
                        </span>
                      </div>
                    </div>
                  </div>
                  {provider.is_active ? (
                    <div className="bg-primary-500 rounded-full p-1">
                      <CheckCircle className="h-3 w-3 text-white" />
                    </div>
                  ) : (
                    <div className="opacity-0 group-hover:opacity-100 transition-opacity">
                      <div className="bg-slate-600 rounded-full p-1">
                        <Play className="h-3 w-3 text-white fill-current" />
                      </div>
                    </div>
                  )}
                </div>
                {provider.is_active && (
                  <div className="absolute inset-x-0 -bottom-px h-1 bg-primary-500 rounded-b-xl" />
                )}
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="card">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6">
          <h2 className="text-lg sm:text-xl font-bold text-white">AI Providers</h2>
          <div className="flex flex-col sm:flex-row items-center gap-2 w-full sm:w-auto">
            <button
              type="button"
              onClick={() => {
                setEditableProviders(providers ? [...providers] : [])
                setIsEditingProviders(true)
              }}
              className="px-4 py-2 bg-slate-800 hover:bg-slate-750 text-slate-300 hover:text-white rounded-xl text-xs font-bold flex items-center space-x-2 transition-all active:scale-95 border border-slate-700 w-full sm:w-auto justify-center"
            >
              <Settings className="h-4 w-4" />
              <span>Edit Engines</span>
            </button>
            <button
              onClick={handleSave}
              disabled={saveMutation.isPending}
              className="btn-primary flex items-center space-x-2 w-full sm:w-auto justify-center disabled:opacity-50"
            >
              {saveMutation.isPending ? (
                <RefreshCw className="h-5 w-5 animate-spin" />
              ) : (
                <Save className="h-5 w-5" />
              )}
              <span>{saveMutation.isPending ? 'Saving Keys...' : 'Save All Keys'}</span>
            </button>
          </div>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {paginatedProviders.map((provider: Provider) => {
            const providerKey = provider.key
            const envVar = provider.env_var
            // Get current value from server using envVar
            const currentValue = (currentKeys as Record<string, string>)?.[envVar] || ''
            // Get value from state using providerKey (unique per provider)
            const stateValue = apiKeys[providerKey]
            // Use state value if exists, otherwise use current value from server
            const inputValue = stateValue !== undefined ? stateValue : currentValue
            const isVisible = visibleKeys[providerKey] || false

            const configuredInfo = configuredProvidersData?.providers.find((p: ConfiguredProvider) => p.key === providerKey)
            const isConfigured = !!configuredInfo
            const isActive = configuredInfo?.is_active

            return (
              <div key={provider.key} className={`bg-slate-700/50 rounded-xl p-5 border-2 transition-all ${isActive ? 'border-primary-500 bg-primary-500/5' : isConfigured ? 'border-slate-600' : 'border-transparent'
                }`}>
                <div className="flex items-start justify-between mb-4">
                  <div className="flex-1">
                    <div className="flex items-center space-x-3 mb-1">
                      <span className="text-3xl">{provider.icon}</span>
                      <div>
                        <div className="flex items-center space-x-2">
                          <h3 className="text-lg font-bold text-white">{provider.name}</h3>
                          {isActive && (
                            <span className="px-2 py-0.5 bg-primary-500 text-white text-[10px] font-bold rounded-full uppercase tracking-wider">
                              Active
                            </span>
                          )}
                          {!isActive && isConfigured && (
                            <span className="px-2 py-0.5 bg-green-500/20 text-green-400 text-[10px] font-bold rounded-full uppercase tracking-wider border border-green-500/30">
                              Configured
                            </span>
                          )}
                        </div>
                        <p className="text-sm text-slate-400">{provider.description}</p>
                      </div>
                    </div>
                    <div className="mt-3 flex flex-wrap items-center gap-y-2 text-xs">
                      <div className="px-2 py-1 bg-slate-800 rounded text-slate-300 mr-3 border border-slate-600">
                        Model: <span className="text-primary-400 font-mono">{provider.model}</span>
                      </div>
                      <a
                        href={provider.api_key_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="text-primary-400 hover:text-primary-300 font-medium flex items-center"
                      >
                        Get API Key <span className="ml-1">→</span>
                      </a>
                    </div>
                  </div>
                  {isConfigured && !isActive && (
                    <button
                      onClick={() => setActiveProviderMutation.mutate(provider.key)}
                      disabled={setActiveProviderMutation.isPending}
                      className={`px-4 py-2 text-white text-xs font-bold rounded-lg shadow-lg transition-all flex items-center space-x-2 active:scale-95 ${setActiveProviderMutation.isPending ? 'bg-slate-700' :
                        setActiveProviderMutation.isSuccess && setActiveProviderMutation.variables === provider.key
                          ? 'bg-emerald-600 shadow-emerald-900/20'
                          : 'bg-primary-600 hover:bg-primary-700 shadow-primary-900/20'
                        }`}
                    >
                      {setActiveProviderMutation.isPending ? (
                        <RefreshCw className="h-3 w-3 animate-spin" />
                      ) : setActiveProviderMutation.isSuccess && setActiveProviderMutation.variables === provider.key ? (
                        <CheckCircle className="h-3 w-3" />
                      ) : (
                        <Play className="h-3 w-3 fill-current" />
                      )}
                      <span>
                        {setActiveProviderMutation.isPending ? 'Working...' :
                          setActiveProviderMutation.isSuccess && setActiveProviderMutation.variables === provider.key ? 'Activated!' : 'Activate'}
                      </span>
                    </button>
                  )}
                </div>
                {/* Multiple API Keys: Show upload option and status for all providers */}
                <div className="mb-4 p-3 bg-slate-600 rounded-lg">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm font-semibold text-white">Multiple API Keys</span>
                    {providerStatuses[providerKey]?.has_keys && (
                      <button
                        onClick={() => refetchProviderStatus(providerKey)}
                        className="p-1 hover:bg-slate-500 rounded"
                        title="Refresh status"
                      >
                        <RefreshCw className="h-4 w-4 text-slate-300" />
                      </button>
                    )}
                  </div>
                  {providerStatuses[providerKey]?.has_keys ? (
                    <div className="text-sm text-slate-300 mb-2">
                      <div className="flex items-center space-x-2">
                        <CheckCircle className="h-4 w-4 text-green-400" />
                        <span>
                          Using API Key {providerStatuses[providerKey].current_key_number} of {providerStatuses[providerKey].count}
                          {providerStatuses[providerKey].current_key_preview && (
                            <span className="text-slate-400 ml-2">
                              ({providerStatuses[providerKey].current_key_preview})
                            </span>
                          )}
                        </span>
                      </div>
                      <p className="text-xs text-slate-400 mt-1">
                        Keys will automatically rotate when rate limited
                      </p>
                    </div>
                  ) : (
                    <p className="text-xs text-slate-400 mb-2">
                      Upload a .txt file with multiple API keys (one per line)
                    </p>
                  )}
                  <div className="flex items-center gap-2">
                    <input
                      type="file"
                      accept=".txt"
                      onChange={handleFileUpload(providerKey)}
                      className="hidden"
                      id={`provider-upload-${providerKey}`}
                    />
                    <label
                      htmlFor={`provider-upload-${providerKey}`}
                      className="px-3 py-2 bg-primary-600 hover:bg-primary-700 rounded-lg text-white text-sm cursor-pointer flex items-center space-x-2"
                    >
                      <Upload className="h-4 w-4" />
                      <span>{uploadProviderMutation.isPending ? 'Uploading...' : 'Upload Keys File'}</span>
                    </label>
                  </div>
                </div>
                <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
                  <input
                    type={isVisible ? 'text' : 'password'}
                    placeholder={envVar === "HF_TOKEN" || provider.name.includes("Gemma") ? "Hugging Face Token (Optional)" : `Enter ${provider.name} API key`}
                    value={inputValue}
                    onChange={(e) => {
                      const newValue = e.target.value
                      // Update all providers that share the same envVar
                      setApiKeys((prev) => {
                        const updated = { ...prev }
                        providers?.forEach((p: Provider) => {
                          if (p.env_var === envVar) {
                            updated[p.key] = newValue
                          }
                        })
                        return updated
                      })
                    }}
                    className="input-field flex-1"
                  />
                  <button
                    onClick={() => handleTestProvider(provider)}
                    disabled={testingProviders[providerKey]}
                    className="px-4 py-2 bg-emerald-600 hover:bg-emerald-700 disabled:bg-slate-600 disabled:cursor-not-allowed rounded-lg text-white flex items-center justify-center sm:flex-shrink-0 transition-colors"
                    title="Test API Key"
                  >
                    {testingProviders[providerKey] ? (
                      <RefreshCw className="h-5 w-5 animate-spin" />
                    ) : (
                      <TestTube2 className="h-5 w-5" />
                    )}
                  </button>
                  <button
                    onClick={() => toggleVisibility(providerKey)}
                    className="px-4 py-2 bg-slate-600 hover:bg-slate-500 rounded-lg text-white flex items-center justify-center sm:flex-shrink-0"
                  >
                    {isVisible ? <EyeOff className="h-5 w-5" /> : <Eye className="h-5 w-5" />}
                  </button>
                </div>
              </div>
            )
          })}
        </div>

        {/* Pagination Controls */}
        {totalPages > 1 && (
          <div className="flex flex-col sm:flex-row items-center justify-between border-t border-slate-700/60 pt-6 mt-6 gap-4">
            <div className="text-xs text-slate-400">
              Showing <span className="font-semibold text-white">{startIndex + 1}</span> to{' '}
              <span className="font-semibold text-white">
                {Math.min(startIndex + pageSize, providers?.length || 0)}
              </span>{' '}
              of <span className="font-semibold text-white">{providers?.length}</span> engines
            </div>
            <div className="flex items-center space-x-1">
              <button
                type="button"
                onClick={() => setCurrentPage(prev => Math.max(prev - 1, 1))}
                disabled={currentPage === 1}
                className="px-3 py-1.5 bg-slate-700/50 hover:bg-slate-700 disabled:opacity-40 disabled:hover:bg-slate-700/50 text-slate-300 hover:text-white rounded-lg text-xs font-bold transition-all"
              >
                Previous
              </button>
              {Array.from({ length: totalPages }).map((_, i) => (
                <button
                  key={i}
                  type="button"
                  onClick={() => setCurrentPage(i + 1)}
                  className={`w-8 h-8 rounded-lg text-xs font-bold transition-all ${
                    currentPage === i + 1
                      ? 'bg-primary-600 text-white'
                      : 'bg-slate-800 text-slate-400 hover:bg-slate-750 hover:text-white'
                  }`}
                >
                  {i + 1}
                </button>
              ))}
              <button
                type="button"
                onClick={() => setCurrentPage(prev => Math.min(prev + 1, totalPages))}
                disabled={currentPage === totalPages}
                className="px-3 py-1.5 bg-slate-700/50 hover:bg-slate-700 disabled:opacity-40 disabled:hover:bg-slate-700/50 text-slate-300 hover:text-white rounded-lg text-xs font-bold transition-all"
              >
                Next
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Edit Providers Modal */}
      {isEditingProviders && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 overflow-y-auto">
          <div className="fixed inset-0 bg-black/80 backdrop-blur-md animate-in fade-in duration-150" onClick={() => setIsEditingProviders(false)} />

          <div className="relative w-full max-w-4xl bg-slate-900 border border-slate-700/60 rounded-2xl shadow-2xl flex flex-col max-h-[85vh] overflow-hidden animate-in zoom-in-95 duration-200">
            {/* Modal Header */}
            <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-805/40">
              <div className="flex items-center space-x-3">
                <div className="p-2 bg-primary-500/10 rounded-lg text-primary-400">
                  <Settings className="h-5 w-5" />
                </div>
                <div>
                  <h3 className="text-lg font-bold text-white">Manage AI Engines</h3>
                  <p className="text-xs text-slate-400">Customize model details, environment keys, and descriptions.</p>
                </div>
              </div>
              <button onClick={() => setIsEditingProviders(false)} className="text-slate-400 hover:text-white transition-colors">
                <X className="h-6 w-6" />
              </button>
            </div>

            {/* Modal Body */}
            <div className="flex-1 p-6 overflow-y-auto space-y-6">
              {/* Quick Guide Alert */}
              <div className="bg-primary-500/10 border border-primary-500/20 rounded-xl overflow-hidden transition-all duration-300">
                <button
                  type="button"
                  onClick={() => setGuideExpanded(!guideExpanded)}
                  className="w-full p-4 flex items-center justify-between hover:bg-primary-500/5 text-xs text-left"
                >
                  <div className="flex items-center space-x-3 text-slate-300">
                    <HelpCircle className="h-5 w-5 text-primary-400 shrink-0" />
                    <div>
                      <p className="font-bold text-white uppercase tracking-wider text-[10px]">Quick Integration Guide</p>
                      <p className="text-[11px] text-slate-400">Click to expand/collapse custom AI integration tips.</p>
                    </div>
                  </div>
                  {guideExpanded ? <ChevronUp className="h-4.5 w-4.5 text-slate-400" /> : <ChevronDown className="h-4.5 w-4.5 text-slate-400" />}
                </button>

                {guideExpanded && (
                  <div className="px-4 pb-4 pt-1 border-t border-primary-500/10 text-xs leading-relaxed text-slate-300 animate-in slide-in-from-top-1 duration-150">
                    <p>To integrate custom AI providers (like SumoPod, Ollama, etc.) successfully:</p>
                    <ul className="list-disc pl-4 space-y-1.5 text-slate-400 mt-2">
                      <li><strong>Model ID:</strong> Always use the provider prefix format, e.g. <code className="text-primary-300 px-1 py-0.5 bg-primary-950/40 rounded">openai/model-name</code> (e.g. <code className="text-primary-300">openai/mimo-v2.5-pro</code>) so LiteLLM processes the API request correctly.</li>
                      <li><strong>API Key Env Variable:</strong> Enter a custom uppercase key name (e.g. <code className="text-primary-300">YOUR_API_KEY</code>). <em>Note: Do not paste the actual API key here.</em> Paste the key on the main dashboard cards after saving these settings.</li>
                      <li><strong>API Key URL:</strong> The URL link where users can register or fetch their API key (e.g. <code className="text-primary-300">https://ai.your.com</code>). This URL will be rendered as a clickable 'Get API Key' link on the dashboard card.</li>
                      <li><strong>API Base URL:</strong> Provide the provider's API base URL ending in <code className="text-primary-300">/v1</code> (e.g. <code className="text-primary-300">https://ai.your.com/v1</code>) so requests route to the correct server.</li>
                    </ul>
                  </div>
                )}
              </div>

              <div className="space-y-4">
                {editableProviders.map((provider, index) => (
                  <div key={provider.key || index} className="p-5 bg-slate-800/50 border border-slate-700/60 rounded-xl relative group">
                    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                      {/* Name */}
                      <div>
                        <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">Engine Name</label>
                        <input
                          type="text"
                          value={provider.name}
                          onChange={(e) => {
                            const val = e.target.value
                            setEditableProviders(prev => {
                              const updated = [...prev]
                              updated[index] = { ...updated[index], name: val }
                              return updated
                            })
                          }}
                          className="w-full bg-slate-900 border border-slate-800 focus:border-primary-500/50 rounded-lg px-3 py-2 text-white text-sm outline-none transition-all"
                          placeholder="e.g. Gemini 2.5 Pro"
                        />
                      </div>

                      {/* Model String */}
                      <div>
                        <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">Model ID (LiteLLM Format)</label>
                        <input
                          type="text"
                          value={provider.model}
                          onChange={(e) => {
                            const val = e.target.value
                            setEditableProviders(prev => {
                              const updated = [...prev]
                              updated[index] = { ...updated[index], model: val }
                              return updated
                            })
                          }}
                          className="w-full bg-slate-900 border border-slate-800 focus:border-primary-500/50 rounded-lg px-3 py-2 text-white text-sm font-mono outline-none transition-all"
                          placeholder="e.g. gemini/gemini-2.5-pro"
                        />
                      </div>

                      {/* Env Var Name */}
                      <div>
                        <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">API Key Env Variable</label>
                        <input
                          type="text"
                          value={provider.env_var}
                          onChange={(e) => {
                            const val = e.target.value
                            setEditableProviders(prev => {
                              const updated = [...prev]
                              updated[index] = { ...updated[index], env_var: val }
                              return updated
                            })
                          }}
                          className="w-full bg-slate-900 border border-slate-800 focus:border-primary-500/50 rounded-lg px-3 py-2 text-white text-sm font-mono outline-none transition-all"
                          placeholder="e.g. GOOGLE_API_KEY"
                        />
                      </div>

                      {/* API Key URL */}
                      <div>
                        <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">API Key URL</label>
                        <input
                          type="text"
                          value={provider.api_key_url}
                          onChange={(e) => {
                            const val = e.target.value
                            setEditableProviders(prev => {
                              const updated = [...prev]
                              updated[index] = { ...updated[index], api_key_url: val }
                              return updated
                            })
                          }}
                          className="w-full bg-slate-900 border border-slate-800 focus:border-primary-500/50 rounded-lg px-3 py-2 text-white text-sm outline-none transition-all"
                          placeholder="e.g. https://aistudio.google.com/apikey"
                        />
                      </div>

                      {/* API Base URL */}
                      <div>
                        <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">API Base URL (Optional)</label>
                        <input
                          type="text"
                          value={provider.api_base || ''}
                          onChange={(e) => {
                            const val = e.target.value
                            setEditableProviders(prev => {
                              const updated = [...prev]
                              updated[index] = { ...updated[index], api_base: val }
                              return updated
                            })
                          }}
                          className="w-full bg-slate-900 border border-slate-800 focus:border-primary-500/50 rounded-lg px-3 py-2 text-white text-sm font-mono outline-none transition-all"
                          placeholder="e.g. https://ai.sumopod.com/v1"
                        />
                      </div>

                      {/* Icon */}
                      <div>
                        <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">Icon (Emoji)</label>
                        <input
                          type="text"
                          value={provider.icon}
                          onChange={(e) => {
                            const val = e.target.value
                            setEditableProviders(prev => {
                              const updated = [...prev]
                              updated[index] = { ...updated[index], icon: val }
                              return updated
                            })
                          }}
                          className="w-full bg-slate-900 border border-slate-800 focus:border-primary-500/50 rounded-lg px-3 py-2 text-white text-sm outline-none transition-all"
                          placeholder="e.g. 🤖"
                        />
                      </div>

                      {/* Description */}
                      <div className="md:col-span-2">
                        <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5">Engine Description</label>
                        <input
                          type="text"
                          value={provider.description}
                          onChange={(e) => {
                            const val = e.target.value
                            setEditableProviders(prev => {
                              const updated = [...prev]
                              updated[index] = { ...updated[index], description: val }
                              return updated
                            })
                          }}
                          className="w-full bg-slate-900 border border-slate-800 focus:border-primary-500/50 rounded-lg px-3 py-2 text-white text-sm outline-none transition-all"
                          placeholder="Short description of this engine's strengths"
                        />
                      </div>

                      {/* Delete Button - Aligned with Description */}
                      <div className="flex items-end">
                        <button
                          type="button"
                          onClick={() => {
                            setEditableProviders(prev => prev.filter((_, i) => i !== index))
                          }}
                          className="w-full py-2 bg-rose-500/10 hover:bg-rose-500 text-rose-500 hover:text-white rounded-lg transition-all active:scale-[0.98] border border-rose-500/20 text-xs font-bold uppercase tracking-wider flex items-center justify-center space-x-1.5 h-[38px]"
                          title="Delete engine"
                        >
                          <Trash2 className="h-4 w-4" />
                          <span>Delete Engine</span>
                        </button>
                      </div>
                    </div>
                  </div>
                ))}
              </div>

              {/* Add New Engine Button */}
              <button
                type="button"
                onClick={() => {
                  setEditableProviders(prev => {
                    const keys = prev.map(p => parseInt(p.key)).filter(k => !isNaN(k))
                    const nextKey = keys.length > 0 ? (Math.max(...keys) + 1).toString() : "1"
                    return [
                      ...prev,
                      {
                        key: nextKey,
                        name: "New AI Engine",
                        model: "provider/model-id",
                        env_var: "NEW_API_KEY",
                        api_key_url: "https://",
                        description: "Custom AI engine configured by user",
                        icon: "⚙️"
                      }
                    ]
                  })
                }}
                className="w-full py-4 border-2 border-dashed border-slate-700 hover:border-primary-500/50 text-slate-400 hover:text-white rounded-xl transition-all flex items-center justify-center space-x-2 font-bold text-xs uppercase tracking-widest active:scale-[0.99]"
              >
                <Plus className="h-4.5 w-4.5" />
                <span>Add Custom Engine</span>
              </button>
            </div>

            {/* Modal Footer */}
            <div className="flex items-center justify-end px-6 py-4 border-t border-slate-800 bg-slate-800/40 gap-3">
              <button
                type="button"
                onClick={() => setIsEditingProviders(false)}
                className="px-5 py-2.5 bg-slate-800 hover:bg-slate-750 text-slate-300 rounded-lg text-xs font-bold uppercase tracking-widest transition-all border border-slate-700 active:scale-95"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => saveProvidersMutation.mutate(editableProviders)}
                disabled={saveProvidersMutation.isPending}
                className="px-6 py-2.5 bg-primary-600 hover:bg-primary-700 text-white rounded-lg text-xs font-bold uppercase tracking-widest transition-all shadow-md active:scale-95 disabled:opacity-50 flex items-center space-x-2"
              >
                {saveProvidersMutation.isPending ? (
                  <RefreshCw className="h-4 w-4 animate-spin" />
                ) : (
                  <Save className="h-4 w-4" />
                )}
                <span>{saveProvidersMutation.isPending ? 'Committing...' : 'Commit Engines'}</span>
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

