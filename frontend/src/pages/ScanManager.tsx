import { useState } from 'react'
import { useQuery, useMutation } from '@tanstack/react-query'
import { scanAPI, templateAPI } from '../api/client'
import { Play, Plus, Target, Settings, Info, Zap, Shield, Wand2, Trash2, RefreshCw, ExternalLink } from 'lucide-react'
import { useToast } from '../context/ToastContext'
import { AxiosError } from 'axios'

interface Template {
  name: string
  size?: number
  preview?: string
}

export default function ScanManager() {
  const [targets, setTargets] = useState<string[]>([''])
  const [instruction, setInstruction] = useState('')
  const [selectedTemplate, setSelectedTemplate] = useState('')
  const [runName, setRunName] = useState('')
  const [nonInteractive, setNonInteractive] = useState(false)
  const [isAutonomous, setIsAutonomous] = useState(true)
  const { showToast } = useToast()

  const { data: templates } = useQuery({
    queryKey: ['templates'],
    queryFn: () => templateAPI.list().then(res => res.data.templates),
  })

  const { data: recentScans } = useQuery({
    queryKey: ['scan-results'],
    queryFn: () => scanAPI.getResults().then(res => res.data.results),
  })

  const scanMutation = useMutation({
    mutationFn: (request: {
      targets: string[]
      instruction?: string
      template?: string
      run_name?: string
      non_interactive: boolean
    }) => scanAPI.start(request),
    onSuccess: (res) => {
      showToast(`Scan "${res.data.scan_id}" started successfully!`, 'success')
      // Reset form
      setTargets([''])
      setInstruction('')
      setSelectedTemplate('')
      setRunName('')
    },
    onError: (error: AxiosError<{ detail: string }>) => {
      showToast(error.response?.data?.detail || 'Failed to start scan', 'error')
    }
  })

  const handleAddTarget = () => {
    setTargets([...targets, ''])
  }

  const handleRemoveTarget = (index: number) => {
    setTargets(targets.filter((_, i) => i !== index))
  }

  const handleTargetChange = (index: number, value: string) => {
    const newTargets = [...targets]
    newTargets[index] = value
    setTargets(newTargets)
  }

  const handleStartScan = () => {
    const validTargets = targets.filter(t => t.trim() !== '')
    if (validTargets.length === 0) {
      showToast('Please add at least one target to scan', 'error')
      return
    }

    if (!isAutonomous && !selectedTemplate && !instruction.trim()) {
      showToast('Please select a template or provide custom directives when Autonomous Mode is disabled.', 'error')
      return
    }

    scanMutation.mutate({
      targets: validTargets,
      instruction: isAutonomous ? undefined : (instruction || undefined),
      template: isAutonomous ? undefined : (selectedTemplate || undefined),
      run_name: runName || undefined,
      non_interactive: nonInteractive,
    })
  }
  return (
    <div className="max-w-6xl mx-auto space-y-6 animate-in fade-in slide-in-from-bottom-4 duration-700">
      <div className="flex flex-col md:flex-row md:items-end justify-between gap-4">
        <div>
          <div className="flex items-center space-x-2 text-primary-500 mb-2">
            <Zap className="h-5 w-5" />
            <span className="text-sm font-semibold uppercase tracking-wider">Mission Control</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-bold text-white tracking-tight">Launch <span className="text-transparent bg-clip-text bg-gradient-to-r from-primary-400 to-primary-600">Scan</span></h1>
          <p className="text-slate-400 mt-1 max-w-xl">Configure your targets and AI instructions to begin a comprehensive security assessment.</p>
        </div>

        <div className="hidden lg:flex items-center space-x-4 text-slate-500 text-xs">
          <div className="flex items-center space-x-1">
            <Shield className="h-3 w-3" />
            <span>AI Powered</span>
          </div>
          <div className="w-1 h-1 bg-slate-700 rounded-full" />
          <div className="flex items-center space-x-1">
            <Zap className="h-3 w-3" />
            <span>Real-time</span>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Left Column: Targets */}
        <div className="lg:col-span-2 space-y-6">
          <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 rounded-2xl overflow-hidden shadow-xl shadow-black/20">
            <div className="p-1 bg-gradient-to-r from-primary-500/20 to-transparent" />
            <div className="p-6">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-primary-500/10 rounded-lg">
                    <Target className="h-6 w-6 text-primary-500" />
                  </div>
                  <div>
                    <h2 className="text-xl font-bold text-white leading-none">Attack Surface</h2>
                    <p className="text-xs text-slate-500 mt-1">Specify URLs, domains, or repositories to test</p>
                  </div>
                </div>
                <div className="px-2 py-1 bg-slate-700/50 rounded text-[10px] font-mono text-slate-400">
                  {targets.filter(t => t.trim()).length} Targets Active
                </div>
              </div>

              <div className="space-y-3">
                {targets.map((target, index) => (
                  <div key={index} className="group relative flex items-center gap-2">
                    <div className="flex-1 relative">
                      <input
                        type="text"
                        placeholder="e.g. https://example.com"
                        value={target}
                        onChange={(e) => handleTargetChange(index, e.target.value)}
                        className="input-field w-full pl-10 h-12 bg-slate-900/50 border-slate-700/50 focus:border-primary-500/50 transition-all rounded-xl"
                      />
                      <div className="absolute left-3.5 top-1/2 -translate-y-1/2 text-slate-600 transition-colors group-focus-within:text-primary-500">
                        <span className="text-xs font-mono">{index + 1}</span>
                      </div>
                    </div>

                    {targets.length > 1 && (
                      <button
                        onClick={() => handleRemoveTarget(index)}
                        className="p-3 text-slate-500 hover:text-primary-400 transition-colors bg-slate-900/50 hover:bg-primary-500/10 rounded-xl border border-slate-700/50"
                        title="Remove Target"
                      >
                        <Trash2 className="h-5 w-5" />
                      </button>
                    )}
                  </div>
                ))}

                <button
                  onClick={handleAddTarget}
                  className="w-full mt-2 p-4 border-2 border-dashed border-slate-700 rounded-2xl text-slate-400 hover:text-primary-500 hover:border-primary-500/50 hover:bg-primary-500/5 transition-all flex items-center justify-center space-x-2 group"
                >
                  <Plus className="h-5 w-5 group-hover:scale-110 transition-transform" />
                  <span className="font-medium">Add Another Target</span>
                </button>
              </div>
            </div>
          </div>

          <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 rounded-2xl overflow-hidden shadow-xl shadow-black/20">
            <div className="p-1 bg-gradient-to-r from-blue-500/20 to-transparent" />
            <div className="p-6">
              <div className="flex items-center space-x-3 mb-6">
                <div className="p-2 bg-blue-500/10 rounded-lg">
                  <Wand2 className="h-6 w-6 text-blue-500" />
                </div>
                <div>
                  <h2 className="text-xl font-bold text-white leading-none">AI Intent</h2>
                  <p className="text-xs text-slate-500 mt-1">Guide the autonomous agent with custom instructions</p>
                </div>
              </div>

              <div className="space-y-6">
                {/* Autonomous Mode Toggle Switch */}
                <div className="flex items-center justify-between p-4 bg-slate-900/40 rounded-xl border border-slate-800">
                  <div>
                    <span className="text-sm font-semibold text-white block">Autonomous Mode</span>
                    <span className="text-[10px] text-slate-500 uppercase tracking-wider font-mono">Deploy agents with default instructions</span>
                  </div>
                  <label className="relative inline-flex items-center cursor-pointer">
                    <input
                      type="checkbox"
                      checked={isAutonomous}
                      onChange={(e) => {
                        setIsAutonomous(e.target.checked)
                        if (e.target.checked) {
                          setSelectedTemplate('')
                          setInstruction('')
                        }
                      }}
                      className="sr-only peer"
                    />
                    <div className="w-11 h-6 bg-slate-800 peer-focus:outline-none rounded-full peer peer-checked:after:translate-x-full peer-checked:after:border-white after:content-[''] after:absolute after:top-[4px] after:left-[4px] after:bg-slate-400 after:border-slate-400 after:border after:rounded-full after:h-4 after:w-4 after:transition-all peer-checked:bg-primary-600 peer-checked:after:bg-white peer-checked:after:border-white" />
                  </label>
                </div>

                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                  <div className={`md:col-span-1 transition-opacity duration-300 ${isAutonomous ? 'opacity-40 pointer-events-none' : ''}`}>
                    <label className="block text-xs font-bold text-slate-400 uppercase tracking-widest mb-2 px-1">
                      Mode Template {!isAutonomous && <span className="text-primary-500 font-bold">*</span>}
                    </label>
                    <select
                      value={selectedTemplate}
                      onChange={(e) => setSelectedTemplate(e.target.value)}
                      disabled={isAutonomous}
                      className="input-field w-full h-11 bg-slate-900/50 border-slate-700/50 rounded-xl cursor-pointer hover:border-blue-500/30 transition-colors text-xs"
                    >
                      <option value="">Select a template...</option>
                      {templates?.map((template: Template) => (
                        <option key={template.name} value={template.name}>
                          {template.name}
                        </option>
                      ))}
                    </select>
                  </div>

                  <div className="md:col-span-1">
                    <label className="block text-xs font-bold text-slate-400 uppercase tracking-widest mb-2 px-1">
                      Run Identifier
                    </label>
                    <input
                      type="text"
                      value={runName}
                      onChange={(e) => setRunName(e.target.value)}
                      placeholder="e.g. Q3-Audit (Optional)"
                      className="input-field w-full h-11 bg-slate-900/50 border-slate-700/50 rounded-xl text-xs"
                    />
                  </div>
                </div>

                <div className={`transition-opacity duration-300 ${isAutonomous ? 'opacity-40 pointer-events-none' : ''}`}>
                  <label className="block text-xs font-bold text-slate-400 uppercase tracking-widest mb-2 px-1">
                    Additional Context / Directives {!isAutonomous && <span className="text-primary-500 font-bold">*</span>}
                  </label>
                  <textarea
                    value={instruction}
                    onChange={(e) => setInstruction(e.target.value)}
                    disabled={isAutonomous}
                    placeholder={isAutonomous ? "Using default system prompt. Disable Autonomous Mode to enter directives." : "Provide specific areas to focus on or ignore (e.g. Test only SQLi)..."}
                    className="input-field w-full h-40 bg-slate-900/50 border-slate-700/50 rounded-2xl resize-none p-4 text-xs placeholder:italic"
                  />
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Right Column: Options & Controls */}
        <div className="space-y-6 lg:sticky lg:top-24 lg:self-start">
          <div className="bg-slate-800/80 backdrop-blur-md border border-slate-700 rounded-2xl overflow-hidden shadow-xl">
            <div className="p-6">
              <div className="flex items-center space-x-3 mb-6">
                <div className="p-2 bg-indigo-500/10 rounded-lg">
                  <Settings className="h-6 w-6 text-indigo-500" />
                </div>
                <h2 className="text-xl font-bold text-white">Execution</h2>
              </div>

              <div className="space-y-6">
                <div className="p-4 bg-slate-900/50 rounded-2xl border border-slate-700/50">
                  <div className="flex items-start space-x-3">
                    <div className="pt-0.5">
                      <input
                        type="checkbox"
                        id="non-interactive"
                        checked={nonInteractive}
                        onChange={(e) => setNonInteractive(e.target.checked)}
                        className="w-5 h-5 text-primary-600 bg-slate-800 border-slate-600 rounded-lg focus:ring-primary-500 cursor-pointer"
                      />
                    </div>
                    <div>
                      <label htmlFor="non-interactive" className="text-sm font-semibold text-white cursor-pointer select-none">
                        Non-interactive Mode
                      </label>
                      <p className="text-xs text-slate-400 mt-1">Headless execution optimized for speed and logging.</p>
                    </div>
                  </div>
                </div>

                <div className="p-4 bg-primary-500/5 rounded-2xl border border-primary-500/20">
                  <div className="flex items-start space-x-3">
                    <Info className="h-5 w-5 text-primary-500 shrink-0 mt-0.5" />
                    <p className="text-xs text-slate-300 leading-relaxed">
                      Launching a scan will deploy autonomous agents to analyze the attack surface. This process is documented in real-time under the <span className="text-primary-400 font-semibold">Results</span> tab.
                    </p>
                  </div>
                </div>

                <div className="pt-2">
                  <button
                    onClick={handleStartScan}
                    disabled={scanMutation.isPending}
                    className="group w-full btn-primary h-16 rounded-2xl flex items-center justify-center space-x-3 text-lg font-bold shadow-lg shadow-primary-500/20 active:scale-[0.98] transition-all disabled:opacity-50 disabled:scale-100"
                  >
                    {scanMutation.isPending ? (
                      <>
                        <div className="h-5 w-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        <span>Initializing...</span>
                      </>
                    ) : (
                      <>
                        <Play className="h-6 w-6 group-hover:fill-current transition-all" />
                        <span>Deploy Agents</span>
                      </>
                    )}
                  </button>
                </div>
              </div>
            </div>
          </div>

          {/* Recent Scans Card */}
          {recentScans && recentScans.length > 0 && (
            <div className="bg-slate-800/50 backdrop-blur-sm border border-slate-700/50 rounded-2xl p-6 shadow-xl shadow-black/20">
              <div className="flex items-center space-x-3 mb-4">
                <div className="p-2 bg-primary-500/10 rounded-lg text-primary-400">
                  <RefreshCw className="h-5 w-5 " />
                </div>
                <div>
                  <h3 className="text-base font-bold text-white tracking-tight uppercase">Recent Audits</h3>
                  <p className="text-[10px] text-slate-500 font-bold uppercase tracking-widest font-mono">Quick Clone & Relaunch</p>
                </div>
              </div>

              <div className="space-y-3">
                {recentScans.slice(0, 3).map((scan: any) => (
                  <div key={scan.name} className="p-4 bg-slate-900/60 border border-slate-800 hover:border-slate-700/80 rounded-xl transition-all flex flex-col gap-2">
                    <div className="flex items-start justify-between gap-2">
                      <div className="min-w-0">
                        <span className="text-xs font-bold text-white block truncate uppercase tracking-tight" title={scan.name}>
                          {scan.name}
                        </span>
                        <span className="text-[10px] text-slate-500 font-mono">
                          {new Date(scan.created * 1000).toLocaleDateString()}
                        </span>
                      </div>
                      <div className="flex items-center space-x-1">
                        <button
                          type="button"
                          onClick={() => {
                            if (scan.targets && scan.targets.length > 0) {
                              setTargets([...scan.targets])
                              setInstruction(scan.user_instructions || '')
                              setSelectedTemplate(scan.template || '')
                              setRunName(scan.name.split('-').slice(0, -1).join('-') || '')
                              setIsAutonomous(!(scan.user_instructions || scan.template))
                              showToast('Scan configuration cloned! Review and Deploy.', 'success')
                            } else {
                              showToast('No target configuration found for this scan.', 'error')
                            }
                          }}
                          className="p-1.5 bg-primary-500/10 hover:bg-primary-500 text-primary-400 hover:text-white rounded-lg transition-all active:scale-90"
                          title="Clone & Relaunch Scan"
                        >
                          <RefreshCw className="h-3.5 w-3.5" />
                        </button>
                        <a
                          href="/results"
                          className="p-1.5 bg-slate-800 hover:bg-slate-750 text-slate-300 hover:text-white rounded-lg transition-all active:scale-90"
                          title="View Results"
                        >
                          <ExternalLink className="h-3.5 w-3.5" />
                        </a>
                      </div>
                    </div>
                    {scan.targets && scan.targets.length > 0 && (
                      <div className="text-[10px] text-slate-400 bg-slate-950/40 p-2 rounded border border-slate-850 truncate font-mono">
                        Target: {scan.targets[0]} {scan.targets.length > 1 ? `(+${scan.targets.length - 1} more)` : ''}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          <div className="p-6 bg-gradient-to-br from-slate-800/40 to-transparent border border-white/5 rounded-2xl">
            <div className="flex items-center space-x-2 text-slate-400 mb-3">
              <Shield className="h-4 w-4" />
              <h4 className="text-xs font-bold uppercase tracking-widest">Active Guard</h4>
            </div>
            <p className="text-[11px] text-slate-500 leading-normal">
              HADES agents operate within a controlled sandbox environment. All scanned data is encrypted and stored locally in your <code>agent_runs</code> directory.
            </p>
          </div>
        </div>
      </div>
    </div>
  )
}

