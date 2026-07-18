import { useState, useEffect } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { settingsAPI, dockerAPI } from '../api/client'
import {
  Save,
  Bell,
  MessageSquare,
  CheckCircle,
  XCircle,
  Sliders,
  Globe,
  Shield,
  Zap,
  Terminal,
  Lock,
  Loader2,
  Cpu,
  AlertTriangle,
  RefreshCw
} from 'lucide-react'
import { useToast } from '../context/ToastContext'

export default function Settings() {
  const queryClient = useQueryClient()
  const { showToast } = useToast()
  const [telegramEnabled, setTelegramEnabled] = useState(false)
  const [telegramToken, setTelegramToken] = useState('')
  const [telegramChatId, setTelegramChatId] = useState('')
  const [discordEnabled, setDiscordEnabled] = useState(false)
  const [discordWebhook, setDiscordWebhook] = useState('')
  const [testResult, setTestResult] = useState<{ type: 'telegram' | 'discord' | null; success: boolean; message: string } | null>(null)

  const { data: settings, isLoading } = useQuery({
    queryKey: ['settings'],
    queryFn: () => settingsAPI.getSettings().then(res => res.data),
  })

  const { data: dockerStatus, isLoading: dockerLoading, refetch: refetchDocker } = useQuery({
    queryKey: ['docker-status'],
    queryFn: () => dockerAPI.getStatus().then(res => res.data),
  })

  useEffect(() => {
    if (settings) {
      setTelegramEnabled(settings.telegram?.enabled || false)
      setTelegramToken(settings.telegram?.token || '')
      setTelegramChatId(settings.telegram?.chat_id || '')
      setDiscordEnabled(settings.discord?.enabled || false)
      setDiscordWebhook(settings.discord?.webhook || '')
    }
  }, [settings])

  const saveMutation = useMutation({
    mutationFn: (data: { telegram: object; discord: object }) => settingsAPI.saveSettings(data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] })
      showToast('Settings saved successfully!', 'success')
    },
    onError: (error: any) => {
      showToast(`Failed to save settings: ${error.response?.data?.detail || error.message}`, 'error')
    },
  })

  const testMutation = useMutation({
    mutationFn: (data: { type: 'telegram' | 'discord' }) => settingsAPI.testNotification(data),
    onSuccess: (_response, variables) => {
      setTestResult({ type: variables.type, success: true, message: 'Test notification sent successfully!' })
      setTimeout(() => setTestResult(null), 5000)
    },
    onError: (error: any, variables) => {
      setTestResult({
        type: variables.type,
        success: false,
        message: error.response?.data?.detail || error.message || 'Failed to send test notification'
      })
      setTimeout(() => setTestResult(null), 5000)
    },
  })

  const handleSave = () => {
    saveMutation.mutate({
      telegram: {
        enabled: telegramEnabled,
        token: telegramToken,
        chat_id: telegramChatId,
      },
      discord: {
        enabled: discordEnabled,
        webhook: discordWebhook,
      },
    })
  }

  const handleTestTelegram = () => {
    if (!telegramToken || !telegramChatId) {
      showToast('Please enter Telegram token and chat ID first', 'error')
      return
    }
    testMutation.mutate({ type: 'telegram' })
  }

  const handleTestDiscord = () => {
    if (!discordWebhook) {
      showToast('Please enter Discord webhook URL first', 'error')
      return
    }
    testMutation.mutate({ type: 'discord' })
  }

  if (isLoading || dockerLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary-500"></div>
      </div>
    )
  }

  return (
    <div className="max-w-6xl mx-auto space-y-6 sm:space-y-8 animate-in fade-in duration-500">
      {/* Title Header */}
      <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 pb-6 border-b border-slate-700/40">
        <div>
          <div className="flex items-center space-x-2 text-primary-500 mb-1.5">
            <Sliders className="h-5 w-5" />
            <span className="text-xs font-bold uppercase tracking-wider text-primary-400">System Directives</span>
          </div>
          <h1 className="text-3xl font-bold text-white tracking-tight">System Settings</h1>
          <p className="text-slate-400 text-sm mt-1 max-w-xl">Configure notification alerts, integration hooks, and isolated sandbox parameters.</p>
        </div>
        <div className="flex items-center space-x-2 bg-emerald-500/10 border border-emerald-500/20 px-3.5 py-1.5 rounded-full">
          <div className="h-2 w-2 bg-emerald-500 rounded-full " />
          <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider">Active</span>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Telegram Configuration */}
        <div className={`rounded-2xl bg-slate-800 border transition-all duration-300 p-6 sm:p-6 ${telegramEnabled ? 'border-primary-500/35 shadow-lg shadow-primary-500/5' : 'border-slate-700/60 shadow-md'}`}>
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center space-x-3.5">
              <div className={`p-2.5 rounded-xl transition-colors ${telegramEnabled ? 'bg-primary-600 text-white' : 'bg-slate-900 text-slate-500'}`}>
                <MessageSquare className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-base font-bold text-white uppercase tracking-tight">Telegram Alerts</h2>
                <p className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider">Encrypted Notifications</p>
              </div>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={telegramEnabled}
                onChange={(e) => setTelegramEnabled(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-10 h-5.5 bg-slate-900 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[4px] after:left-[4px] after:bg-slate-400 after:border-slate-400 after:border after:rounded-full after:h-3.5 after:w-3.5 after:transition-all peer-checked:bg-primary-600 peer-checked:after:bg-white peer-checked:after:border-white" />
            </label>
          </div>

          <div className="space-y-5">
            <div>
              <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5 flex items-center space-x-1.5">
                <Lock className="h-3 w-3 text-slate-550" />
                <span>Bot Token</span>
              </label>
              <input
                type="password"
                value={telegramToken}
                onChange={(e) => setTelegramToken(e.target.value)}
                placeholder="e.g. 123456:ABC-def..."
                className="w-full bg-slate-900 border border-slate-700/60 focus:border-primary-500/50 rounded-xl px-4 py-2.5 text-white text-xs font-mono placeholder:text-slate-700 transition-all outline-none"
                disabled={!telegramEnabled}
              />
              <p className="text-[10px] text-slate-500 mt-1.5 ml-1">Generate via @BotFather on Telegram</p>
            </div>

            <div>
              <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5 flex items-center space-x-1.5">
                <Globe className="h-3 w-3 text-slate-550" />
                <span>Chat ID</span>
              </label>
              <input
                type="text"
                value={telegramChatId}
                onChange={(e) => setTelegramChatId(e.target.value)}
                placeholder="e.g. -100123456"
                className="w-full bg-slate-900 border border-slate-700/60 focus:border-primary-500/50 rounded-xl px-4 py-2.5 text-white text-xs font-mono placeholder:text-slate-700 transition-all outline-none"
                disabled={!telegramEnabled}
              />
              <p className="text-[10px] text-slate-500 mt-1.5 ml-1">Identify your Chat ID using @userinfobot</p>
            </div>

            <div className="pt-2">
              <button
                type="button"
                onClick={handleTestTelegram}
                disabled={!telegramEnabled || !telegramToken || !telegramChatId || testMutation.isPending}
                className={`w-full py-3 rounded-xl font-bold text-[10px] uppercase tracking-wider transition-all flex items-center justify-center space-x-2 active:scale-[0.98] ${
                  telegramEnabled
                    ? 'bg-slate-900 hover:bg-primary-600 text-white border border-slate-700/60 hover:border-transparent'
                    : 'bg-slate-800/30 text-slate-600 border border-slate-800/40 cursor-not-allowed'
                }`}
              >
                {testMutation.isPending && testResult?.type === 'telegram' ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : testResult?.type === 'telegram' ? (
                  testResult.success ? <CheckCircle className="h-3.5 w-3.5 text-emerald-400" /> : <XCircle className="h-3.5 w-3.5 text-rose-500" />
                ) : (
                  <Bell className="h-3.5 w-3.5" />
                )}
                <span>Test Connection</span>
              </button>
              {testResult?.type === 'telegram' && (
                <p className={`text-center mt-2.5 text-[10px] font-bold uppercase tracking-wider ${testResult.success ? 'text-emerald-400' : 'text-rose-500'}`}>
                  {testResult.message}
                </p>
              )}
            </div>
          </div>
        </div>

        {/* Discord Configuration */}
        <div className={`rounded-2xl bg-slate-800 border transition-all duration-300 p-6 sm:p-6 ${discordEnabled ? 'border-primary-500/35 shadow-lg shadow-primary-500/5' : 'border-slate-700/60 shadow-md'}`}>
          <div className="flex items-center justify-between mb-6">
            <div className="flex items-center space-x-3.5">
              <div className={`p-2.5 rounded-xl transition-colors ${discordEnabled ? 'bg-primary-600 text-white' : 'bg-slate-900 text-slate-500'}`}>
                <Terminal className="h-5 w-5" />
              </div>
              <div>
                <h2 className="text-base font-bold text-white uppercase tracking-tight">Discord Bridge</h2>
                <p className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider">Webhook Propagation</p>
              </div>
            </div>
            <label className="relative inline-flex items-center cursor-pointer">
              <input
                type="checkbox"
                checked={discordEnabled}
                onChange={(e) => setDiscordEnabled(e.target.checked)}
                className="sr-only peer"
              />
              <div className="w-10 h-5.5 bg-slate-900 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[4px] after:left-[4px] after:bg-slate-400 after:border-slate-400 after:border after:rounded-full after:h-3.5 after:w-3.5 after:transition-all peer-checked:bg-primary-600 peer-checked:after:bg-white peer-checked:after:border-white" />
            </label>
          </div>

          <div className="space-y-5">
            <div>
              <label className="block text-[10px] font-bold text-slate-400 uppercase tracking-widest mb-1.5 flex items-center space-x-1.5">
                <Shield className="h-3 w-3 text-slate-550" />
                <span>Webhook URL</span>
              </label>
              <input
                type="password"
                value={discordWebhook}
                onChange={(e) => setDiscordWebhook(e.target.value)}
                placeholder="e.g. https://discord.com/api/webhooks/..."
                className="w-full bg-slate-900 border border-slate-700/60 focus:border-primary-500/50 rounded-xl px-4 py-2.5 text-white text-xs font-mono placeholder:text-slate-700 transition-all outline-none"
                disabled={!discordEnabled}
              />
              <p className="text-[10px] text-slate-500 mt-1.5 ml-1">Generate via Server Integrations in Discord settings</p>
            </div>

            <div className="pt-[106px] hidden sm:block" /> {/* Layout balance spacing */}

            <div className="pt-2">
              <button
                type="button"
                onClick={handleTestDiscord}
                disabled={!discordEnabled || !discordWebhook || testMutation.isPending}
                className={`w-full py-3 rounded-xl font-bold text-[10px] uppercase tracking-wider transition-all flex items-center justify-center space-x-2 active:scale-[0.98] ${
                  discordEnabled
                    ? 'bg-slate-900 hover:bg-primary-600 text-white border border-slate-700/60 hover:border-transparent'
                    : 'bg-slate-800/30 text-slate-600 border border-slate-800/40 cursor-not-allowed'
                }`}
              >
                {testMutation.isPending && testResult?.type === 'discord' ? (
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                ) : testResult?.type === 'discord' ? (
                  testResult.success ? <CheckCircle className="h-3.5 w-3.5 text-emerald-400" /> : <XCircle className="h-3.5 w-3.5 text-rose-500" />
                ) : (
                  <Zap className="h-3.5 w-3.5" />
                )}
                <span>Test Connection</span>
              </button>
              {testResult?.type === 'discord' && (
                <p className={`text-center mt-2.5 text-[10px] font-bold uppercase tracking-wider ${testResult.success ? 'text-emerald-400' : 'text-rose-500'}`}>
                  {testResult.message}
                </p>
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Sandbox Infrastructure Status */}
      <div className="rounded-2xl bg-slate-800 border border-slate-700/60 shadow-md p-6 sm:p-6">
        <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 mb-6 pb-6 border-b border-slate-700/40">
          <div className="flex items-center space-x-3.5">
            <div className="p-2.5 bg-primary-500/10 rounded-xl text-primary-450">
              <Shield className="h-5.5 w-5.5" />
            </div>
            <div>
              <h2 className="text-lg font-bold text-white uppercase tracking-tight">Sandbox Infrastructure</h2>
              <p className="text-[10px] text-slate-500 font-semibold uppercase tracking-wider font-mono">Isolated Container Environment</p>
            </div>
          </div>
          <button
            type="button"
            onClick={() => refetchDocker()}
            className="px-4 py-2 bg-slate-900 hover:bg-slate-750 text-slate-300 font-semibold rounded-xl text-xs flex items-center space-x-2 transition-all active:scale-95 border border-slate-700"
          >
            <RefreshCw className="h-3.5 w-3.5" />
            <span>Sync Docker</span>
          </button>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {/* Engine Card */}
          <div className="p-5 bg-slate-900/50 border border-slate-700/40 rounded-xl flex items-center justify-between gap-4">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-primary-500/10 rounded-lg text-primary-400">
                <Cpu className="h-4.5 w-4.5" />
              </div>
              <div>
                <h3 className="font-semibold text-white text-xs uppercase tracking-tight">Docker Engine</h3>
                <p className="text-[10px] text-slate-500">Core Runtime</p>
              </div>
            </div>
            <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-950/40 border border-slate-800">
              <div className={`h-1.5 w-1.5 rounded-full ${dockerStatus?.docker_installed ? 'bg-green-500 ' : 'bg-rose-500'}`} />
              <span className={`text-[9px] font-bold tracking-wider ${dockerStatus?.docker_installed ? 'text-green-400' : 'text-rose-400'}`}>
                {dockerStatus?.docker_installed ? 'READY' : 'MISSING'}
              </span>
            </div>
          </div>

          {/* Socket Card */}
          <div className="p-5 bg-slate-900/50 border border-slate-700/40 rounded-xl flex items-center justify-between gap-4">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-primary-500/10 rounded-lg text-primary-400">
                <Zap className="h-4.5 w-4.5" />
              </div>
              <div>
                <h3 className="font-semibold text-white text-xs uppercase tracking-tight">Daemon Socket</h3>
                <p className="text-[10px] text-slate-500">Process Monitor</p>
              </div>
            </div>
            <div className="flex items-center gap-1.5 px-3 py-1 rounded-full bg-slate-950/40 border border-slate-800">
              <div className={`h-1.5 w-1.5 rounded-full ${dockerStatus?.docker_running ? 'bg-green-500 ' : 'bg-rose-500'}`} />
              <span className={`text-[9px] font-bold tracking-wider ${dockerStatus?.docker_running ? 'text-green-400' : 'text-rose-400'}`}>
                {dockerStatus?.docker_running ? 'ACTIVE' : 'OFFLINE'}
              </span>
            </div>
          </div>
        </div>

        {/* Provisioning block if Docker is not installed */}
        {!dockerStatus?.docker_installed && (
          <div className="relative overflow-hidden rounded-xl bg-slate-950/30 border border-slate-700/40 p-5 mt-4">
            <div className="flex items-center space-x-2 text-primary-400 mb-3 font-bold uppercase text-[10px] tracking-wider">
              <Terminal className="h-3.5 w-3.5" />
              <span>Provisioning Directives</span>
            </div>
            <div className="space-y-3.5 font-mono text-xs leading-relaxed text-slate-400">
              <div className="p-3 bg-black/35 rounded-lg select-all cursor-pointer hover:text-slate-200 transition-colors">
                $ curl -fsSL https://get.docker.com | sudo sh
              </div>
              <p className="text-[9px] text-primary-500/70 italic px-1">Execute as root in your terminal node to initialize the environment.</p>
            </div>
          </div>
        )}

        {/* Socket Lost Warning */}
        {!dockerStatus?.docker_running && dockerStatus?.error && (
          <div className="p-4 bg-rose-500/5 border border-rose-500/20 rounded-xl flex items-start space-x-3 mt-4">
            <AlertTriangle className="h-4.5 w-4.5 text-rose-500 shrink-0 mt-0.5" />
            <div>
              <p className="text-[10px] font-bold text-rose-400 uppercase tracking-widest mb-0.5">System Fault</p>
              <p className="text-xs text-slate-400 font-mono leading-relaxed">{dockerStatus.error}</p>
            </div>
          </div>
        )}

        {dockerStatus?.docker_running && (
          <div className="grid grid-cols-2 gap-4 mt-4">
            <div className="p-3.5 bg-slate-900/30 rounded-xl border border-slate-700/40">
              <p className="text-[9px] font-bold text-slate-550 uppercase mb-0.5">Heartbeat Connection</p>
              <p className="text-emerald-400 font-mono text-xs font-bold tracking-widest">STABLE</p>
            </div>
            <div className="p-3.5 bg-slate-900/30 rounded-xl border border-slate-700/40">
              <p className="text-[9px] font-bold text-slate-550 uppercase mb-0.5">Average Latency</p>
              <p className="text-slate-300 font-mono text-xs">0.42ms</p>
            </div>
          </div>
        )}
      </div>

      {/* Save Settings Bar */}
      <div className="flex flex-col sm:flex-row items-center justify-between gap-4 p-6 rounded-2xl bg-slate-800 border border-slate-700/60 shadow-lg relative overflow-hidden">
        <div className="relative flex items-center space-x-3.5">
          <div className="p-2.5 bg-primary-600/10 rounded-xl text-primary-400">
            <Lock className="h-5.5 w-5.5" />
          </div>
          <div>
            <h3 className="text-base font-bold text-white uppercase tracking-tight">Commit Directives</h3>
            <p className="text-[10px] font-bold text-slate-500 uppercase tracking-wider">Write configuration settings permanently to storage node</p>
          </div>
        </div>
        <button
          onClick={handleSave}
          disabled={saveMutation.isPending}
          className="w-full sm:w-auto px-8 py-3.5 bg-primary-600 hover:bg-primary-700 text-white font-bold rounded-xl transition-all shadow-md active:scale-95 flex items-center justify-center space-x-2 text-xs uppercase tracking-widest disabled:opacity-50"
        >
          {saveMutation.isPending ? (
            <Loader2 className="h-4.5 w-4.5 animate-spin" />
          ) : (
            <Save className="h-4.5 w-4.5" />
          )}
          <span>{saveMutation.isPending ? 'Committing...' : 'Commit Settings'}</span>
        </button>
      </div>
    </div>
  )
}
