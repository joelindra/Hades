import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { templateAPI } from '../api/client'
import { AxiosError } from 'axios'
import { Plus, Edit, Trash2, Eye, Save, X, AlertCircle, FileCode, Scroll, Zap, Shield, Sparkles } from 'lucide-react'
import { useToast } from '../context/ToastContext'

interface Template {
  name: string
  size: number
  preview: string
  content: string
}

export default function Templates() {
  const [editing, setEditing] = useState<string | null>(null)
  const [creating, setCreating] = useState(false)
  const [viewing, setViewing] = useState<string | null>(null)
  const [toDelete, setToDelete] = useState<string | null>(null)
  const [formData, setFormData] = useState({ name: '', content: '' })
  const queryClient = useQueryClient()
  const { showToast } = useToast()

  const { data, isLoading } = useQuery({
    queryKey: ['templates'],
    queryFn: () => templateAPI.list().then(res => res.data.templates),
  })

  const createMutation = useMutation({
    mutationFn: ({ name, content }: { name: string; content: string }) =>
      templateAPI.create(name, content),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['templates'] })
      setCreating(false)
      setFormData({ name: '', content: '' })
      showToast('Template created successfully!', 'success')
    },
    onError: (error: AxiosError<{ detail: string }>) => {
      showToast(error.response?.data?.detail || 'Failed to create template', 'error')
    }
  })

  const updateMutation = useMutation({
    mutationFn: ({ name, content }: { name: string; content: string }) =>
      templateAPI.update(name, content),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['templates'] })
      setEditing(null)
      showToast('Template updated successfully!', 'success')
    },
    onError: (error: AxiosError<{ detail: string }>) => {
      showToast(error.response?.data?.detail || 'Failed to update template', 'error')
    }
  })

  const deleteMutation = useMutation({
    mutationFn: (name: string) => templateAPI.delete(name),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['templates'] })
      setToDelete(null)
      showToast('Template deleted successfully', 'success')
    },
    onError: (error: AxiosError<{ detail: string }>) => {
      showToast(error.response?.data?.detail || 'Failed to delete template', 'error')
    }
  })

  const handleCreate = () => {
    if (!formData.name || !formData.content) {
      showToast('Please fill in both name and content', 'error')
      return
    }
    if (formData.name.includes(' ')) {
      showToast('Template name cannot contain spaces. Use underscores (_) instead.', 'error')
      return
    }
    createMutation.mutate(formData)
  }

  const handleUpdate = (name: string) => {
    if (formData.content) {
      updateMutation.mutate({ name, content: formData.content })
    }
  }

  const handleEdit = async (name: string) => {
    const res = await templateAPI.get(name)
    setFormData({ name, content: res.data.content })
    setEditing(name)
  }

  const handleView = async (name: string) => {
    const res = await templateAPI.get(name)
    setFormData({ name, content: res.data.content })
    setViewing(name)
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary-500"></div>
      </div>
    )
  }

  return (
    <div className="relative space-y-8 animate-in fade-in duration-700">
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 pb-6 border-b border-primary-500/10">
        <div>
          <div className="flex items-center space-x-2 text-primary-500 mb-2">
            <Scroll className="h-5 w-5" />
            <span className="text-xs font-bold uppercase tracking-widest text-primary-400">Payload Registry</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-bold text-white tracking-tight">Mission <span className="text-primary-500">Templates</span></h1>
          <p className="text-slate-400 mt-1 max-w-xl">Configure custom directives and specialized logic for your autonomous agents.</p>
        </div>
        <button
          onClick={() => {
            setCreating(true)
            setFormData({ name: '', content: '' })
          }}
          className="group relative px-6 py-3 bg-primary-600 hover:bg-primary-700 text-white font-bold rounded-xl transition-all shadow-lg shadow-primary-600/20 active:scale-95 flex items-center space-x-2 overflow-hidden"
        >
          <div className="absolute inset-0 bg-gradient-to-r from-red-400/0 via-white/10 to-red-400/0 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700" />
          <Plus className="h-5 w-5" />
          <span>New Template</span>
        </button>
      </div>

      {/* Confirmation Modal (Purge) */}
      {toDelete && (
        <div className="fixed inset-0 z-[100] flex items-center justify-center p-4 overflow-y-auto">
          <div className="fixed inset-0 bg-black/95 backdrop-blur-xl animate-in fade-in duration-500" onClick={() => setToDelete(null)} />
          <div className="relative w-full max-w-md bg-slate-900/40 backdrop-blur-2xl border border-primary-500/40 rounded-[2.5rem] shadow-[0_0_50px_-12px_rgba(220,38,38,0.5)] overflow-hidden animate-in zoom-in-95 slide-in-from-bottom-10 duration-300">
            <div className="p-10 text-center relative">
              <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-32 h-32 bg-primary-600/20 rounded-full blur-[80px] pointer-events-none" />

              <div className="relative inline-block mb-8">
                <div className="absolute inset-0 bg-primary-600 rounded-full blur-3xl opacity-30 animate-pulse" />
                <div className="relative h-20 w-20 bg-gradient-to-br from-primary-600 to-red-900 border-2 border-primary-400/30 rounded-full flex items-center justify-center mx-auto shadow-[0_0_30px_rgba(220,38,38,0.4)] transition-transform hover:scale-110">
                  <Trash2 className="h-10 w-10 text-white animate-pulse" />
                </div>
              </div>

              <div className="relative space-y-3 mb-10">
                <h3 className="text-3xl font-bold text-white tracking-tighter uppercase italic">
                  Critical <span className="text-primary-500 drop-shadow-[0_0_8px_rgba(239,68,68,0.5)]">Purge</span>
                </h3>
                <div className="flex items-center justify-center space-x-2">
                  <div className="h-[1px] w-8 bg-primary-500/30" />
                  <span className="text-[10px] font-bold text-primary-500/80 uppercase tracking-[0.3em]">System Lockdown Protocol</span>
                  <div className="h-[1px] w-8 bg-primary-500/30" />
                </div>
              </div>

              <p className="text-slate-300 text-sm mb-10 leading-relaxed font-medium">
                Terminate logic node <span className="text-white font-bold bg-primary-500/20 px-2 py-0.5 rounded border border-primary-500/30">"{toDelete}"</span>?
                <br />
                <span className="text-primary-400/80 text-[11px] font-bold uppercase tracking-wider mt-2 block italic">Action is permanent & irreversible.</span>
              </p>

              <div className="flex flex-col gap-3">
                <button
                  onClick={() => deleteMutation.mutate(toDelete)}
                  disabled={deleteMutation.isPending}
                  className="group relative h-14 bg-primary-600 hover:bg-primary-500 disabled:bg-red-800/50 text-white font-bold rounded-2xl transition-all shadow-[0_0_20px_rgba(220,38,38,0.3)] active:scale-95 flex items-center justify-center space-x-3 overflow-hidden"
                >
                  <div className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent -translate-x-full group-hover:animate-[shimmer_1.5s_infinite]" />
                  {deleteMutation.isPending ? (
                    <div className="h-6 w-6 border-3 border-white/30 border-t-white rounded-full animate-spin" />
                  ) : (
                    <>
                      <Sparkles className="h-5 w-5" />
                      <span className="uppercase tracking-widest text-sm">Initiate Purge</span>
                    </>
                  )}
                </button>
                <button
                  onClick={() => setToDelete(null)}
                  className="h-14 bg-slate-800/50 hover:bg-slate-700/50 text-slate-400 hover:text-white font-bold rounded-2xl transition-all border border-slate-700/50 active:scale-95 uppercase tracking-widest text-xs"
                >
                  Abort Protocol
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Create/Edit Modal */}
      {(creating || editing) && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={() => { setCreating(false); setEditing(null) }} />
          <div className="relative w-full max-w-2xl bg-slate-900 border border-primary-500/30 rounded-2xl shadow-2xl shadow-slate-900/20 overflow-hidden animate-in zoom-in-95 duration-200">
            <div className="p-1 bg-gradient-to-r from-primary-600 to-transparent" />
            <div className="p-6 sm:p-6">
              <div className="flex items-center justify-between mb-8">
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-primary-500/10 rounded-lg">
                    <FileCode className="h-6 w-6 text-primary-500" />
                  </div>
                  <div>
                    <h2 className="text-2xl font-bold text-white leading-none">
                      {creating ? 'Forge New Template' : 'Refine Template'}
                    </h2>
                    <p className="text-xs text-slate-500 mt-1 uppercase tracking-wider font-bold">
                      {creating ? 'Initialize autonomous logic' : `Modifying ${editing}`}
                    </p>
                  </div>
                </div>
                <button
                  onClick={() => {
                    setCreating(false)
                    setEditing(null)
                    setFormData({ name: '', content: '' })
                  }}
                  className="p-2 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-white transition-colors"
                >
                  <X className="h-6 w-6" />
                </button>
              </div>

              <div className="space-y-6">
                {creating && (
                  <div>
                    <label className="block text-xs font-bold text-primary-400 uppercase tracking-widest mb-2 px-1">
                      Template Identifier
                    </label>
                    <input
                      type="text"
                      placeholder="e.g. STEALTH_RECON (No spaces)"
                      value={formData.name}
                      onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                      className={`input-field w-full h-12 bg-slate-950 border-slate-700 focus:border-primary-500/40 transition-all rounded-xl font-mono ${formData.name.includes(' ') ? 'border-primary-500 ring-1 ring-red-500' : ''}`}
                    />
                    {formData.name.includes(' ') && (
                      <p className="text-primary-400 text-xs mt-2 flex items-center px-1 font-semibold">
                        <AlertCircle className="h-3.5 w-3.5 mr-1" />
                        Space detected. Use underscores (_) or hyphens (-) instead.
                      </p>
                    )}
                  </div>
                )}

                <div>
                  <label className="block text-xs font-bold text-primary-400 uppercase tracking-widest mb-2 px-1">
                    Directives & logic
                  </label>
                  <textarea
                    placeholder="Enter instructions for the AI agents..."
                    value={formData.content}
                    onChange={(e) => setFormData({ ...formData, content: e.target.value })}
                    className="input-field w-full h-64 bg-slate-950 border-slate-700 focus:border-primary-500/40 transition-all rounded-2xl p-4 font-mono text-sm leading-relaxed"
                    rows={10}
                  />
                </div>

                <div className="flex items-center gap-3 pt-2">
                  <button
                    onClick={creating ? handleCreate : () => handleUpdate(editing!)}
                    className="flex-1 px-6 py-4 bg-primary-600 hover:bg-primary-700 text-white font-bold rounded-xl transition-all shadow-lg shadow-primary-500/10 active:scale-95 flex items-center justify-center space-x-2"
                  >
                    <Save className="h-5 w-5" />
                    <span>Deploy Logic</span>
                  </button>
                  <button
                    onClick={() => {
                      setCreating(false)
                      setEditing(null)
                      setFormData({ name: '', content: '' })
                    }}
                    className="px-6 py-4 bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold rounded-xl transition-all border border-slate-700"
                  >
                    Cancel
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* View Modal */}
      {viewing && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" onClick={() => setViewing(null)} />
          <div className="relative w-full max-w-3xl bg-slate-900 border border-slate-700/60 rounded-2xl shadow-2xl overflow-hidden animate-in fade-in duration-200">
            <div className="p-6 sm:p-6">
              <div className="flex items-center justify-between mb-6">
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-primary-500/10 rounded-lg">
                    <Zap className="h-6 w-6 text-primary-500" />
                  </div>
                  <h2 className="text-2xl font-bold text-white">Template: {viewing}</h2>
                </div>
                <button onClick={() => setViewing(null)} className="p-2 hover:bg-slate-800 rounded-lg text-slate-400 hover:text-white">
                  <X className="h-6 w-6" />
                </button>
              </div>
              <div className="bg-slate-950 p-6 rounded-2xl border border-slate-800 max-h-[60vh] overflow-y-auto">
                <pre className="text-sm text-slate-200/70 whitespace-pre-wrap font-mono leading-loose">
                  {formData.content}
                </pre>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Templates List */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {data?.map((template: Template) => (
          <div key={template.name} className="group relative overflow-hidden rounded-2xl bg-gradient-to-br from-slate-800/80 to-slate-900/80 border border-slate-700/40 hover:border-primary-500/40 transition-all duration-300 shadow-xl hover:shadow-slate-900/20">
            <div className="absolute inset-0 bg-gradient-to-br from-primary-600/0 to-primary-600/5 opacity-0 group-hover:opacity-100 transition-opacity" />

            <div className="relative p-6">
              <div className="flex items-start justify-between mb-6">
                <div className="flex items-center space-x-3">
                  <div className="p-2 bg-primary-500/10 rounded-lg group-hover:bg-primary-500/20 transition-colors">
                    <Shield className="h-6 w-6 text-primary-500" />
                  </div>
                  <div>
                    <h3 className="text-lg font-bold text-white leading-none">{template.name}</h3>
                    <div className="flex items-center space-x-2 mt-1.5 font-mono text-[10px] text-slate-500">
                      <span className="text-primary-400/70">{template.size} BYTES</span>
                      <span className="w-1 h-1 bg-slate-700 rounded-full" />
                      <span>LOGIC-NODE</span>
                    </div>
                  </div>
                </div>
                <div className="h-2 w-2 bg-primary-500 rounded-full opacity-0 group-hover:opacity-100 transition-all group-hover:scale-125 " />
              </div>

              <div className="relative h-24 overflow-hidden mb-6 bg-slate-950/50 rounded-xl border border-slate-700/50 group-hover:border-slate-700/60 transition-colors">
                <p className="p-3 text-xs text-slate-500 group-hover:text-slate-400 transition-colors font-mono leading-relaxed line-clamp-4">
                  {template.preview}
                </p>
                <div className="absolute inset-0 bg-gradient-to-t from-slate-950 to-transparent opacity-60 pointer-events-none" />
              </div>

              <div className="flex items-center gap-2">
                <button
                  onClick={() => handleView(template.name)}
                  className="flex-1 flex items-center justify-center space-x-2 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold text-xs rounded-lg border border-slate-700 transition-all active:scale-95"
                >
                  <Eye className="h-3.5 w-3.5" />
                  <span>Inspect</span>
                </button>
                <button
                  onClick={() => handleEdit(template.name)}
                  className="flex-1 flex items-center justify-center space-x-2 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 font-bold text-xs rounded-lg border border-slate-700 transition-all active:scale-95"
                >
                  <Edit className="h-3.5 w-3.5" />
                  <span>Modify</span>
                </button>
                <button
                  onClick={() => setToDelete(template.name)}
                  className="p-2.5 bg-red-950/30 hover:bg-primary-600 group/del text-primary-500 hover:text-white rounded-lg border border-slate-700/60 transition-all active:scale-95"
                  title="Purge Template"
                >
                  <Trash2 className="h-4 w-4 transition-transform group-hover/del:scale-110" />
                </button>
              </div>
            </div>
          </div>
        ))}

        {data?.length === 0 && (
          <div className="lg:col-span-3 border-2 border-dashed border-slate-700/60 rounded-2xl p-12 text-center bg-slate-900/50">
            <div className="relative inline-block mb-6">
              <Scroll className="h-16 w-16 text-primary-500/10" />
              <div className="absolute inset-0 flex items-center justify-center">
                <Sparkles className="h-8 w-8 text-primary-500/20" />
              </div>
            </div>
            <h3 className="text-xl font-bold text-white mb-2">No Payloads Found</h3>
            <p className="text-slate-400 mb-8 max-w-sm mx-auto text-sm">Create a template to define specialized instructions for your penetration testing agents.</p>
            <button
              onClick={() => setCreating(true)}
              className="px-8 py-3 bg-primary-600 hover:bg-primary-700 text-white font-bold rounded-xl transition-all shadow-lg active:scale-95"
            >
              Forge First Template
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

