import { useState } from 'react'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { scanAPI } from '../api/client'
import {
  FolderOpen,
  Trash2,
  Download,
  FileSpreadsheet,
  FileText,
  ChevronLeft,
  ChevronRight,
  AlertTriangle,
  X,
  Loader2,
  
  Zap,
  Shield,
  Calendar,
  Layers,
  Eye
} from 'lucide-react'

export default function ScanResults() {
  const queryClient = useQueryClient()
  const [deleting, setDeleting] = useState<string | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<string | null>(null)
  const [previewPdfUrl, setPreviewPdfUrl] = useState<string | null>(null)
  const [previewName, setPreviewName] = useState<string | null>(null)
  const [isPreviewLoading, setIsPreviewLoading] = useState(false)
  const [showSuccessToast, setShowSuccessToast] = useState(false)
  const [showErrorToast, setShowErrorToast] = useState(false)
  const [errorMessage, setErrorMessage] = useState('')
  const [currentPage, setCurrentPage] = useState(1)
  const itemsPerPage = 10

  const { data, isLoading } = useQuery({
    queryKey: ['scan-results'],
    queryFn: () => scanAPI.getResults().then(res => res.data.results),
  })

  const deleteMutation = useMutation({
    mutationFn: (resultName: string) => scanAPI.deleteResult(resultName),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['scan-results'] })
      setDeleting(null)
      setDeleteConfirm(null)
      setShowSuccessToast(true)
      setTimeout(() => setShowSuccessToast(false), 3000)
    },
    onError: (error: unknown) => {
      const err = error as { response?: { data?: { detail?: string } }; message: string }
      setDeleting(null)
      setDeleteConfirm(null)
      setErrorMessage(err.response?.data?.detail || err.message || 'Failed to delete scan result')
      setShowErrorToast(true)
      setTimeout(() => setShowErrorToast(false), 5000)
    },
  })

  const handleDelete = (resultName: string) => {
    setDeleteConfirm(resultName)
  }

  const confirmDelete = () => {
    if (deleteConfirm) {
      setDeleting(deleteConfirm)
      deleteMutation.mutate(deleteConfirm)
    }
  }

  const cancelDelete = () => {
    setDeleteConfirm(null)
  }

  const handleExport = async (resultName: string) => {
    try {
      const response = await scanAPI.exportResult(resultName)
      const blob = new Blob([response.data], { type: 'text/markdown' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${resultName}_report.md`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string } }; message: string }
      const errorMessage = err.response?.data?.detail || err.message
      alert(`Failed to export: ${errorMessage}`)
    }
  }

  const handleExportCSV = async (resultName: string) => {
    try {
      const response = await scanAPI.exportCSV(resultName)
      const blob = new Blob([response.data], { type: 'text/csv' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${resultName}_vulnerabilities.csv`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string }; status?: number }; message: string }
      // Use status from error.response if available
      const status = err.response?.status
      const errorMessage = err.response?.data?.detail || err.message
      if (status === 404) {
        alert('No vulnerabilities found. This scan did not discover any vulnerabilities.')
      } else {
        alert(`Failed to export CSV: ${errorMessage}`)
      }
    }
  }

  const handleExportPDF = async (resultName: string) => {
    try {
      const response = await scanAPI.exportPDF(resultName)
      const blob = new Blob([response.data], { type: 'application/pdf' })
      const url = window.URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `${resultName}_report.pdf`
      document.body.appendChild(a)
      a.click()
      window.URL.revokeObjectURL(url)
      document.body.removeChild(a)
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string }; status?: number }; message: string }
      const status = err.response?.status
      const errorMessage = err.response?.data?.detail || err.message
      if (status === 500 && errorMessage.includes('weasyprint')) {
        alert('PDF generation requires weasyprint. Please install it on the server.')
      } else {
        alert(`Failed to export PDF: ${errorMessage}`)
      }
    }
  }

  const handlePreviewPDF = async (resultName: string) => {
    setIsPreviewLoading(true)
    setPreviewName(resultName)
    try {
      const response = await scanAPI.exportPDF(resultName)
      const blob = new Blob([response.data], { type: 'application/pdf' })
      const url = window.URL.createObjectURL(blob)
      setPreviewPdfUrl(url)
    } catch (error: unknown) {
      const err = error as { response?: { data?: { detail?: string }; status?: number }; message: string }
      const status = err.response?.status
      const errorMessage = err.response?.data?.detail || err.message
      if (status === 500 && errorMessage.includes('weasyprint')) {
        alert('PDF preview requires weasyprint. Please install it on the server.')
      } else {
        alert(`Failed to preview PDF: ${errorMessage}`)
      }
      setPreviewName(null)
    } finally {
      setIsPreviewLoading(false)
    }
  }

  const closePreview = () => {
    if (previewPdfUrl) {
      window.URL.revokeObjectURL(previewPdfUrl)
    }
    setPreviewPdfUrl(null)
    setPreviewName(null)
  }

  const formatDate = (timestamp: number) => {
    const date = new Date(timestamp * 1000)
    return {
      date: date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' }),
      time: date.toLocaleTimeString('en-US', { hour: '2-digit', minute: '2-digit' })
    }
  }

  const formatFileSize = (bytes: number) => {
    if (bytes === 0) return '0 B'
    const k = 1024
    const sizes = ['B', 'KB', 'MB', 'GB']
    const i = Math.floor(Math.log(bytes) / Math.log(k))
    return Math.round(bytes / Math.pow(k, i) * 100) / 100 + ' ' + sizes[i]
  }

  const getFileType = (name: string) => {
    if (name.includes('vulnerabilities')) return 'CSV'
    if (name.includes('report')) return 'Report'
    return 'Scan Result'
  }

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary-500"></div>
      </div>
    )
  }

  // Pagination logic
  const totalPages = data ? Math.ceil(data.length / itemsPerPage) : 0
  const startIndex = (currentPage - 1) * itemsPerPage
  const endIndex = startIndex + itemsPerPage

  return (
    <div className="relative space-y-8 animate-in fade-in duration-700">
      {/* Success Toast */}
      {showSuccessToast && (
        <div className="fixed top-4 right-4 z-[100] animate-slide-in-right">
          <div className="bg-slate-900 text-white px-6 py-4 rounded-2xl shadow-2xl flex items-center space-x-3 min-w-[320px] border border-green-500/50">
            <div className="flex-shrink-0 w-10 h-10 rounded-xl bg-green-500/10 flex items-center justify-center">
              <Shield className="w-5 h-5 text-green-500" />
            </div>
            <div className="flex-1">
              <p className="font-bold text-sm">ARCHIVE PURGED</p>
              <p className="text-xs text-slate-400">Scan result successfully deleted</p>
            </div>
          </div>
        </div>
      )}

      {/* Error Toast */}
      {showErrorToast && (
        <div className="fixed top-4 right-4 z-[100] animate-slide-in-right">
          <div className="bg-slate-900 text-white px-6 py-4 rounded-2xl shadow-2xl flex items-center space-x-3 min-w-[320px] border border-primary-500/40">
            <div className="flex-shrink-0 w-10 h-10 rounded-xl bg-primary-500/10 flex items-center justify-center">
              <AlertTriangle className="w-5 h-5 text-primary-500" />
            </div>
            <div className="flex-1">
              <p className="font-bold text-sm">ACCESS FAILED</p>
              <p className="text-xs text-slate-400">{errorMessage}</p>
            </div>
            <button onClick={() => setShowErrorToast(false)} className="text-slate-500 hover:text-white">
              <X className="h-4 w-4" />
            </button>
          </div>
        </div>
      )}

      {/* Hero Section */}
      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 pb-6 border-b border-slate-700/40">
        <div>
          <div className="flex items-center space-x-2 text-primary-500 mb-2">
            <Layers className="h-5 w-5" />
            <span className="text-xs font-bold uppercase tracking-widest text-primary-400">Scan Archive</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-bold text-white tracking-tight">Scan <span className="text-primary-500">Repository</span></h1>
          <p className="text-slate-400 mt-1 max-w-xl">Review and export detailed security reports and vulnerability data from historical operations.</p>
        </div>
        <div className="flex items-center space-x-3">
          <div className="px-4 py-2 bg-primary-500/10 border border-primary-500/30 rounded-xl">
            <p className="text-[10px] text-primary-400 font-bold uppercase tracking-wider">Database Node</p>
            <p className="text-lg font-bold text-white">{data?.length || 0} ITEMS</p>
          </div>
        </div>
      </div>

      {(!data || data.length === 0) ? (
        <div className="relative overflow-hidden rounded-2xl bg-slate-900 border border-slate-800 p-16 text-center shadow-2xl">
          <div className="absolute inset-0 bg-[radial-gradient(circle_at_center,rgba(220,38,38,0.05)_0%,transparent_70%)]" />
          <div className="relative">
            <div className="relative inline-block mb-8">
              <div className="absolute inset-0 bg-primary-600 rounded-full opacity-0" />
              <FolderOpen className="h-20 w-20 text-slate-700 relative" />
            </div>
            <h3 className="text-2xl font-bold text-white mb-3 tracking-tight">Archive Empty</h3>
            <p className="text-slate-500 mb-8 max-w-sm mx-auto leading-relaxed">No historical scan data detected on this node. Initialize a new operation to populate the repository.</p>
            <a href="/scan" className="group relative inline-flex items-center space-x-3 px-8 py-4 bg-primary-600 hover:bg-primary-700 text-white font-bold rounded-2xl transition-all shadow-xl shadow-primary-500/10 active:scale-95 overflow-hidden">
              <div className="absolute inset-0 bg-gradient-to-r from-red-400/0 via-white/10 to-red-400/0 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700" />
              <Zap className="h-5 w-5 fill-current" />
              <span>Initialize Operation</span>
            </a>
          </div>
        </div>
      ) : (
        <div className="space-y-6">
          {/* File Browser Style Table */}
          <div className="relative overflow-hidden rounded-2xl bg-slate-900/50 backdrop-blur-md border border-slate-800 shadow-2xl overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="bg-slate-950/50 border-b border-slate-800">
                  <th className="px-6 py-5 text-[10px] font-bold text-slate-500 uppercase tracking-[0.2em]">Deployment Identity</th>
                  <th className="px-6 py-5 text-[10px] font-bold text-slate-500 uppercase tracking-[0.2em]">Node Type</th>
                  <th className="px-6 py-5 text-[10px] font-bold text-slate-500 uppercase tracking-[0.2em]"><div className="flex items-center space-x-2"><Calendar className="h-3 w-3" /><span>Timestamp</span></div></th>
                  <th className="px-6 py-5 text-[10px] font-bold text-slate-500 uppercase tracking-[0.2em]">Byte Size</th>
                  <th className="px-6 py-5 text-[10px] font-bold text-slate-500 uppercase tracking-[0.2em] text-right">Data Export</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50">
                {data.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage).map((result: { name: string; created: number; size?: number; path: string; has_findings?: boolean }) => {
                  const dateInfo = formatDate(result.created)
                  const fileSize = result.size || 0
                  const fileType = getFileType(result.name)
                  const hasFindings = result.has_findings !== false

                  return (
                    <tr key={result.name} className="group hover:bg-primary-600/[0.02] transition-colors cursor-default">
                      <td className="px-6 py-4">
                        <div className="flex items-center space-x-4">
                          <div className="relative">
                            <div className="absolute inset-0 bg-primary-500 rounded-xl blur-lg opacity-0 group-hover:opacity-20 transition-opacity" />
                            <div className="relative p-2.5 bg-slate-800 group-hover:bg-primary-500/10 rounded-xl border border-slate-700 group-hover:border-primary-500/30 transition-all">
                              <FolderOpen className="h-5 w-5 text-slate-500 group-hover:text-primary-500 transition-colors" />
                            </div>
                          </div>
                          <div className="min-w-0">
                            <div className="text-sm font-bold text-white group-hover:text-slate-100 transition-colors uppercase tracking-tight">{result.name}</div>
                            <div className="text-[10px] text-slate-500 font-mono mt-0.5 truncate">{result.path}</div>
                          </div>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span className={`px-2.5 py-1 rounded-full text-[10px] font-bold uppercase tracking-widest border ${fileType === 'Report' ? 'bg-indigo-500/10 border-indigo-500/30 text-indigo-400' :
                          fileType === 'CSV' ? 'bg-green-500/10 border-green-500/30 text-green-400' :
                            'bg-slate-800 border-slate-700 text-slate-400'
                          }`}>
                          {fileType}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <div className="text-xs font-mono text-slate-400">
                          <div className="text-slate-300">{dateInfo.date}</div>
                          <div className="text-[10px] opacity-50">{dateInfo.time}</div>
                        </div>
                      </td>
                      <td className="px-6 py-4">
                        <span className="text-xs font-mono text-slate-400 tracking-tighter">
                          {formatFileSize(fileSize)}
                        </span>
                      </td>
                      <td className="px-6 py-4">
                        <div className="flex items-center justify-end space-x-1">
                          <button
                            onClick={() => handlePreviewPDF(result.name)}
                            disabled={isPreviewLoading && previewName === result.name}
                            className="p-2 hover:bg-slate-800 rounded-lg transition-all group/btn"
                            title="Intelligence Preview"
                          >
                            {isPreviewLoading && previewName === result.name ? (
                              <Loader2 className="h-4 w-4 text-white animate-spin" />
                            ) : (
                              <Eye className="h-4 w-4 text-slate-500 group-hover/btn:text-primary-400" />
                            )}
                          </button>
                          <button
                            onClick={() => handleExport(result.name)}
                            disabled={!hasFindings}
                            className="p-2 hover:bg-slate-800 rounded-lg transition-all disabled:opacity-20 group/btn"
                            title="Download Markdown Report"
                          >
                            <Download className="h-4 w-4 text-slate-500 group-hover/btn:text-primary-400" />
                          </button>
                          <button
                            onClick={() => handleExportPDF(result.name)}
                            className="p-2 hover:bg-slate-800 rounded-lg transition-all group/btn"
                            title="Analyze PDF Report"
                          >
                            <FileText className="h-4 w-4 text-slate-500 group-hover/btn:text-white" />
                          </button>
                          <button
                            onClick={() => handleExportCSV(result.name)}
                            disabled={!hasFindings}
                            className="p-2 hover:bg-slate-800 rounded-lg transition-all disabled:opacity-20 group/btn"
                            title="Export Vulnerability Ledger"
                          >
                            <FileSpreadsheet className="h-4 w-4 text-slate-500 group-hover/btn:text-green-400" />
                          </button>
                          <div className="w-px h-4 bg-slate-800 mx-1" />
                          <button
                            onClick={() => handleDelete(result.name)}
                            disabled={deleting === result.name}
                            className="p-2 hover:bg-primary-500/10 rounded-lg transition-all group/del"
                            title="Purge Archive"
                          >
                            <Trash2 className="h-4 w-4 text-slate-600 group-hover/del:text-primary-500" />
                          </button>
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>

            {/* Pagination Controls */}
            {totalPages > 1 && (
              <div className="px-6 py-4 bg-slate-950/30 border-t border-slate-800 flex items-center justify-between">
                <div className="text-[10px] font-bold text-slate-500 uppercase tracking-widest">
                  {startIndex + 1}-{Math.min(endIndex, data.length)} OF {data.length} OPERATIONS
                </div>
                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => setCurrentPage(prev => Math.max(1, prev - 1))}
                    disabled={currentPage === 1}
                    className="p-2.5 bg-slate-800 hover:bg-slate-700 rounded-xl border border-slate-700 transition-all disabled:opacity-20"
                  >
                    <ChevronLeft className="h-4 w-4 text-white" />
                  </button>
                  <div className="flex items-center space-x-1 font-mono text-xs">
                    {Array.from({ length: totalPages }, (_, i) => i + 1).map((page) => (
                      <button
                        key={page}
                        onClick={() => setCurrentPage(page)}
                        className={`w-8 h-8 rounded-lg transition-all ${currentPage === page
                          ? 'bg-primary-600 text-white font-bold'
                          : 'text-slate-500 hover:text-white hover:bg-slate-800'}`}
                      >
                        {page}
                      </button>
                    ))}
                  </div>
                  <button
                    onClick={() => setCurrentPage(prev => Math.min(totalPages, prev + 1))}
                    disabled={currentPage === totalPages}
                    className="p-2.5 bg-slate-800 hover:bg-slate-700 rounded-xl border border-slate-700 transition-all disabled:opacity-20"
                  >
                    <ChevronRight className="h-4 w-4 text-white" />
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Delete Modal - Redesign */}
      {deleteConfirm && (
        <div className="fixed inset-0 z-[200] flex items-center justify-center p-4">
          <div className="absolute inset-0 bg-black/90 backdrop-blur-md" onClick={cancelDelete} />
          <div className="relative w-full max-w-md bg-slate-900 border border-primary-500/40 rounded-[2.5rem] shadow-[0_0_100px_rgba(220,38,38,0.2)] overflow-hidden animate-in zoom-in-95 duration-200">
            <div className="p-1 bg-gradient-to-r from-primary-600 via-primary-800 to-primary-600" />
            <div className="p-10 text-center">
              <div className="relative inline-block mb-6">
                <div className="absolute inset-0 bg-primary-600 rounded-full opacity-0" />
                <div className="relative p-5 bg-primary-600 rounded-2xl shadow-lg">
                  <Shield className="h-10 w-10 text-white" />
                </div>
              </div>
              <h3 className="text-3xl font-bold text-white mb-2 tracking-tight uppercase">Archive Purge</h3>
              <p className="text-primary-400 font-bold text-[10px] uppercase tracking-widest mb-6">Irreversible Data Destruction</p>

              <div className="bg-red-950/30 rounded-2xl p-5 mb-8 border border-slate-700/60 text-sm font-mono leading-relaxed text-slate-200/70">
                Are you sure you want to terminate <span className="text-white font-bold">"{deleteConfirm}"</span>? This will permanently erase the operation history.
              </div>

              <div className="grid grid-cols-2 gap-4">
                <button
                  onClick={confirmDelete}
                  disabled={deleting === deleteConfirm}
                  className="px-6 py-4 bg-primary-600 hover:bg-primary-700 text-white font-bold rounded-2xl transition-all shadow-xl shadow-primary-500/10 active:scale-95 flex items-center justify-center space-x-2"
                >
                  {deleting === deleteConfirm ? <Loader2 className="w-5 h-5 animate-spin" /> : <span>PURGE</span>}
                </button>
                <button
                  onClick={cancelDelete}
                  className="px-6 py-4 bg-slate-800 hover:bg-slate-700 text-slate-400 font-bold rounded-2xl border border-slate-700 transition-all"
                >
                  ABORT
                </button>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* PDF Preview Modal - Elegant Centered Glassmorphism */}
      {previewPdfUrl && (
        <div className="fixed inset-0 z-[300] flex items-center justify-center p-4 sm:p-6 animate-in fade-in duration-500">
          {/* Transparent Backdrop for closing */}
          <div
            className="absolute inset-0 bg-transparent"
            onClick={closePreview}
          />

          {/* Modal Container */}
          <div className="relative w-full max-w-4xl h-full max-h-[90vh] bg-slate-900/90 border border-primary-500/30 rounded-[2rem] shadow-[0_0_100px_rgba(220,38,38,0.15)] flex flex-col overflow-hidden animate-in zoom-in-95 duration-300">
            {/* Elegant Header */}
            <div className="flex items-center justify-between px-8 py-5 border-b border-slate-700/40 bg-gradient-to-r from-primary-600/10 via-transparent to-red-950/20">
              <div className="flex items-center space-x-5">
                <div className="relative">
                  <div className="absolute inset-0 bg-primary-500 rounded-2xl blur-lg opacity-20" />
                  <div className="relative p-3 bg-primary-600 rounded-2xl border border-red-400/30 shadow-lg shadow-primary-500/10">
                    <FileText className="h-6 w-6 text-white" />
                  </div>
                </div>
                <div>
                  <div className="flex items-center space-x-2">
                    <h3 className="text-lg font-bold text-white uppercase tracking-tighter">Intelligence <span className="text-primary-500">Analysis</span></h3>
                    <div className="px-2 py-0.5 bg-primary-500/10 border border-slate-700/60 rounded text-[10px] text-primary-400 font-bold tracking-widest uppercase">Secret</div>
                  </div>
                  <p className="text-[10px] text-slate-500 font-mono tracking-wider">{previewName}</p>
                </div>
              </div>

              <div className="flex items-center space-x-4">
                <button
                  onClick={() => previewName && handleExportPDF(previewName)}
                  className="group relative flex items-center space-x-2 px-5 py-2.5 bg-slate-800 hover:bg-slate-700 text-slate-300 hover:text-white rounded-xl border border-slate-700 transition-all text-xs font-bold tracking-widest overflow-hidden"
                >
                  <div className="absolute inset-0 bg-gradient-to-r from-red-500/0 via-white/5 to-red-500/0 translate-x-[-100%] group-hover:translate-x-[100%] transition-transform duration-700" />
                  <Download className="h-4 w-4" />
                  <span className="hidden sm:inline">EXPORT PDF</span>
                </button>
                <div className="w-px h-8 bg-slate-800" />
                <button
                  onClick={closePreview}
                  className="p-3 bg-primary-500/5 hover:bg-primary-600 text-primary-500 hover:text-white rounded-xl border border-slate-700/60 transition-all active:scale-90"
                >
                  <X className="h-5 w-5" />
                </button>
              </div>
            </div>

            {/* PDF Viewer Container */}
            <div className="flex-1 bg-slate-950/50 p-6 flex items-center justify-center relative overflow-hidden">
              {/* Subtle inner glow */}
              <div className="absolute inset-0 pointer-events-none bg-[radial-gradient(circle_at_center,rgba(220,38,38,0.03)_0%,transparent_70%)]" />

              {/* The actual PDF view */}
              <div className="w-full h-full rounded-xl overflow-hidden border border-slate-800 bg-white shadow-inner">
                <iframe
                  src={`${previewPdfUrl}#toolbar=0&navpanes=0`}
                  className="w-full h-full"
                  title="Intelligence Report Preview"
                />
              </div>
            </div>

            {/* Modal Footer / Status bar */}
            <div className="px-8 py-3 bg-slate-900 border-t border-slate-800 flex items-center justify-between text-[10px] font-mono uppercase tracking-[0.2em] text-slate-500">
              <div className="flex items-center space-x-2">
                <div className="w-1.5 h-1.5 rounded-full bg-primary-500 " />
                <span>Secure Preview Active</span>
              </div>
              <div className="flex items-center space-x-4">
                <span>Node: {previewName?.split('_')[0] || 'Unknown'}</span>
                <span className="text-slate-400">// END OF SCAN SUMMARY</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
