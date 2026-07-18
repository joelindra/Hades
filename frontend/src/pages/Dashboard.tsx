import { useQuery } from '@tanstack/react-query'
import { systemAPI, dockerAPI, activityAPI } from '../api/client'
import { Activity, Server, CheckCircle, XCircle, AlertCircle, Shield, Zap, Target, TrendingUp, Sparkles } from 'lucide-react'
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

export default function Dashboard() {
  const { data: systemInfo } = useQuery({
    queryKey: ['system-info'],
    queryFn: () => systemAPI.getInfo().then(res => res.data),
  })

  const { data: dockerStatus } = useQuery({
    queryKey: ['docker-status'],
    queryFn: () => dockerAPI.getStatus().then(res => res.data),
  })

  const { data: activityData } = useQuery({
    queryKey: ['activity'],
    queryFn: () => activityAPI.getActivity().then(res => res.data),
  })

  return (
    <div className="relative min-h-screen">
      <div className="relative space-y-6 sm:space-y-8">
        {/* Hero Header */}
        <div className="relative overflow-hidden rounded-2xl bg-gradient-to-r from-slate-800 to-slate-900 border border-slate-700/60 shadow-xl">
          <div className="relative p-6 sm:p-10">
            <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6">
              <div className="flex items-center space-x-5">
                <div className="relative">
                  <div className="absolute inset-0 bg-primary-500 rounded-2xl blur-lg opacity-25" />
                  <div className="relative p-4 bg-gradient-to-br from-primary-500 to-primary-600 rounded-xl shadow-md">
                    <Shield className="h-8 w-8 text-white " />
                  </div>
                </div>
                <div>
                  <div className="flex items-center space-x-3 mb-1">
                    <h1 className="text-3xl font-bold text-white tracking-tight">
                      Hades Security
                    </h1>
                    <div className="px-2.5 py-0.5 bg-primary-500/10 border border-primary-500/20 rounded-full">
                      <span className="text-xs font-semibold text-primary-400">v{systemInfo?.version || '1.0.0'}</span>
                    </div>
                  </div>
                  <p className="text-slate-400 text-sm sm:text-base">
                    Autonomous security testing and vulnerability assessment interface.
                  </p>
                </div>
              </div>

              <div className="flex items-center space-x-2 bg-emerald-500/10 border border-emerald-500/20 px-3 py-1.5 rounded-full">
                <div className="h-2 w-2 bg-emerald-500 rounded-full " />
                <span className="text-xs font-semibold text-emerald-400 uppercase tracking-wider">System Active</span>
              </div>
            </div>
          </div>
        </div>

        {/* System Status Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-6">
          {/* Version Card */}
          <div className="group relative overflow-hidden rounded-xl bg-slate-800 border border-slate-700/60 hover:border-primary-500/30 transition-all duration-300 shadow-md">
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="p-2 bg-primary-500/10 rounded-lg text-primary-400">
                  <Activity className="h-5 w-5" />
                </div>
                <div className="h-1.5 w-1.5 bg-primary-500 rounded-full" />
              </div>
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">System Version</p>
              <p className="text-2xl font-bold text-white">{systemInfo?.version || '1.0.0'}</p>
            </div>
          </div>

          {/* Sandbox Status Card */}
          <div className="group relative overflow-hidden rounded-xl bg-slate-800 border border-slate-700/60 hover:border-primary-500/30 transition-all duration-300 shadow-md">
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="p-2 bg-primary-500/10 rounded-lg text-primary-400">
                  <Server className="h-5 w-5" />
                </div>
                {dockerStatus?.docker_running ? (
                  <CheckCircle className="h-5 w-5 text-emerald-500" />
                ) : (
                  <XCircle className="h-5 w-5 text-rose-500" />
                )}
              </div>
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">Sandbox Status</p>
              <p className="text-2xl font-bold text-white">
                {dockerStatus?.docker_running ? 'Active' : 'Offline'}
              </p>
            </div>
          </div>

          {/* Docker Running Card */}
          <div className="group relative overflow-hidden rounded-xl bg-slate-800 border border-slate-700/60 hover:border-primary-500/30 transition-all duration-300 shadow-md">
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="p-2 bg-primary-500/10 rounded-lg text-primary-400">
                  <Zap className="h-5 w-5" />
                </div>
                {dockerStatus?.docker_installed ? (
                  <CheckCircle className="h-5 w-5 text-emerald-500" />
                ) : (
                  <AlertCircle className="h-5 w-5 text-amber-500" />
                )}
              </div>
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">Container Engine</p>
              <p className="text-2xl font-bold text-white">
                {dockerStatus?.docker_installed ? 'Ready' : 'Missing'}
              </p>
            </div>
          </div>

          {/* Image Available Card */}
          <div className="group relative overflow-hidden rounded-xl bg-slate-800 border border-slate-700/60 hover:border-primary-500/30 transition-all duration-300 shadow-md">
            <div className="p-6">
              <div className="flex items-center justify-between mb-4">
                <div className="p-2 bg-primary-500/10 rounded-lg text-primary-400">
                  <Target className="h-5 w-5" />
                </div>
                <div className="h-1.5 w-1.5 bg-primary-400 rounded-full" />
              </div>
              <p className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">Sandbox Image</p>
              <p className="text-2xl font-bold text-white">
                {dockerStatus?.docker_image_available ? 'Loaded' : 'N/A'}
              </p>
            </div>
          </div>
        </div>

        {/* Activity Chart */}
        <div className="rounded-xl bg-slate-800 border border-slate-700/60 shadow-lg">
          <div className="p-6 sm:p-6">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6">
              <div className="flex items-center space-x-3">
                <div className="p-2 bg-primary-500/10 rounded-lg text-primary-400">
                  <TrendingUp className="h-5 w-5" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-white">Activity Monitor</h2>
                  <p className="text-xs text-slate-400">Last 30 Days Performance</p>
                </div>
              </div>
              {activityData?.total_scans !== undefined && (
                <div className="px-4 py-2 bg-slate-900 border border-slate-700/60 rounded-lg self-start">
                  <p className="text-[10px] text-slate-400 font-bold uppercase tracking-wider">Total Scans</p>
                  <p className="text-xl font-bold text-white">{activityData.total_scans}</p>
                </div>
              )}
            </div>

            {activityData?.activity ? (
              <div className="w-full" style={{ height: '300px' }}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={activityData.activity}>
                    <defs>
                      <linearGradient id="scanGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#4f46e5" stopOpacity={0.2} />
                        <stop offset="95%" stopColor="#4f46e5" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="#334155" opacity={0.2} />
                    <XAxis
                      dataKey="date"
                      stroke="#94a3b8"
                      tick={{ fill: '#94a3b8', fontSize: 11 }}
                      angle={-45}
                      textAnchor="end"
                      height={70}
                    />
                    <YAxis stroke="#94a3b8" tick={{ fill: '#94a3b8', fontSize: 11 }} />
                    <Tooltip
                      contentStyle={{
                        backgroundColor: '#1e293b',
                        border: '1px solid #334155',
                        borderRadius: '8px',
                        color: '#f8fafc',
                        boxShadow: '0 4px 12px rgba(0, 0, 0, 0.5)'
                      }}
                    />
                    <Legend wrapperStyle={{ color: '#f8fafc', paddingTop: '10px' }} />
                    <Line
                      type="monotone"
                      dataKey="scans"
                      stroke="#6366f1"
                      strokeWidth={2}
                      name="Security Scans"
                      dot={{ fill: '#6366f1', r: 4, strokeWidth: 1, stroke: '#fff' }}
                      activeDot={{ r: 6, strokeWidth: 1, stroke: '#fff' }}
                      fill="url(#scanGradient)"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            ) : (
              <div className="text-center py-16 text-slate-500">
                <Sparkles className="h-10 w-10 mx-auto mb-3 opacity-30" />
                <p className="text-sm">No activity data available</p>
              </div>
            )}
          </div>
        </div>

        {/* Quick Actions */}
        <div className="rounded-xl bg-slate-800 border border-slate-700/60 shadow-lg">
          <div className="p-6 sm:p-6">
            <div className="flex items-center space-x-3 mb-6">
              <div className="p-2 bg-primary-500/10 rounded-lg text-primary-400">
                <Sparkles className="h-5 w-5" />
              </div>
              <h2 className="text-xl font-bold text-white">Quick Actions</h2>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              <a
                href="/templates"
                className="group relative block p-6 bg-slate-900 hover:bg-slate-900/60 border border-slate-700/60 hover:border-primary-500/30 rounded-xl transition-all duration-300"
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="p-2 bg-primary-500/10 rounded-lg text-primary-400 group-hover:bg-primary-500/20 transition-colors">
                    <Shield className="h-5 w-5" />
                  </div>
                </div>
                <h3 className="font-semibold text-white mb-1.5 text-base">Manage Templates</h3>
                <p className="text-xs text-slate-400 leading-relaxed">Create and edit scan instruction templates for security agents.</p>
              </a>

              <a
                href="/api-config"
                className="group relative block p-6 bg-slate-900 hover:bg-slate-900/60 border border-slate-700/60 hover:border-primary-500/30 rounded-xl transition-all duration-300"
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="p-2 bg-primary-500/10 rounded-lg text-primary-400 group-hover:bg-primary-500/20 transition-colors">
                    <Server className="h-5 w-5" />
                  </div>
                </div>
                <h3 className="font-semibold text-white mb-1.5 text-base">Configure API Keys</h3>
                <p className="text-xs text-slate-400 leading-relaxed">Set up LLM credentials for your AI autonomous security agents.</p>
              </a>

              <a
                href="/scan"
                className="group relative block p-6 bg-primary-950/20 hover:bg-primary-950/45 border border-primary-500/20 hover:border-primary-500/40 rounded-xl transition-all duration-300"
              >
                <div className="flex items-center justify-between mb-3">
                  <div className="p-2 bg-primary-500/20 rounded-lg text-primary-300 group-hover:bg-primary-500/30 transition-colors ">
                    <Target className="h-5 w-5" />
                  </div>
                </div>
                <h3 className="font-semibold text-white mb-1.5 text-base">Start New Scan</h3>
                <p className="text-xs text-primary-300 leading-relaxed">Launch a new automated security audit on your target.</p>
              </a>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
