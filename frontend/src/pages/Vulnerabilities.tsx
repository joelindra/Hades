import { useState, Fragment } from 'react'
import { useQuery } from '@tanstack/react-query'
import { vulnerabilitiesAPI } from '../api/client'
import { AlertTriangle, Shield, Zap, Activity, Target, AlertCircle, ChevronDown, ChevronUp, Terminal, FileText } from 'lucide-react'
import { PieChart, Pie, Cell, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts'

const COLORS = {
  critical: '#F43F5E', // rose-500
  high: '#F97316',     // orange-500
  medium: '#EAB308',   // yellow-500
  low: '#38BDF8'       // sky-400
}

export default function Vulnerabilities() {
  const [expandedRow, setExpandedRow] = useState<string | null>(null)

  const parseBoldAndCode = (text: string) => {
    const regex = /(\*\*.*?\*\*|`.*?`)/g
    const matches = text.split(regex)

    return matches.map((part, index) => {
      if (part.startsWith('**') && part.endsWith('**')) {
        return (
          <strong key={index} className="font-bold text-white">
            {part.slice(2, -2)}
          </strong>
        )
      }
      if (part.startsWith('`') && part.endsWith('`')) {
        return (
          <code key={index} className="px-1.5 py-0.5 bg-slate-950/50 text-primary-400 font-mono text-[10px] rounded border border-slate-800/40">
            {part.slice(1, -1)}
          </code>
        )
      }
      return part
    })
  }

  const renderFormattedMarkdown = (text: string) => {
    if (!text) return null
    const lines = text.split('\n')
    const processedLines: any[] = []

    let inCodeBlock = false
    let currentCodeLines: string[] = []

    for (let i = 0; i < lines.length; i++) {
      const line = lines[i]
      const trimmed = line.trim()

      if (trimmed.startsWith('```')) {
        if (inCodeBlock) {
          processedLines.push({
            type: 'code',
            content: currentCodeLines.join('\n')
          })
          currentCodeLines = []
          inCodeBlock = false
        } else {
          inCodeBlock = true
        }
        continue
      }

      if (inCodeBlock) {
        currentCodeLines.push(line)
        continue
      }

      if (/^[=\-\s]{3,}$/.test(trimmed)) {
        processedLines.push({ type: 'divider' })
        continue
      }

      if (!trimmed) {
        processedLines.push({ type: 'empty' })
        continue
      }

      const isUppercaseHeader = /^[A-Z\s_]{4,30}$/.test(trimmed)
      if (isUppercaseHeader || trimmed.startsWith('##') || trimmed.startsWith('###')) {
        const cleanHeader = trimmed.replace(/^##+\s*/, '')
        processedLines.push({
          type: 'header',
          content: cleanHeader
        })
        continue
      }

      const metadataMatch = trimmed.match(/^([A-Z\s_]{3,20}):\s*(.*)$/)
      if (metadataMatch) {
        processedLines.push({
          type: 'metadata',
          key: metadataMatch[1].trim(),
          value: metadataMatch[2].trim()
        })
        continue
      }

      if (/^\d+\.\s+/.test(trimmed)) {
        const content = trimmed.replace(/^\d+\.\s+/, '')
        const numMatch = trimmed.match(/^\d+/)
        processedLines.push({
          type: 'numbered-list',
          number: numMatch ? numMatch[0] : '1',
          content: content
        })
        continue
      }

      if (trimmed.startsWith('-') || trimmed.startsWith('*')) {
        const content = trimmed.replace(/^[-*]\s*/, '')
        processedLines.push({
          type: 'bullet-list',
          content: content
        })
        continue
      }

      if (/^\d+\/tcp\s+\w+\s+\w+/.test(trimmed) || trimmed === 'PORT STATE SERVICE') {
        let consoleLines = [trimmed]
        while (i + 1 < lines.length && (
          /^\d+\/tcp\s+\w+\s+\w+/.test(lines[i+1].trim()) ||
          lines[i+1].trim() === '' ||
          /^\d+\s+other\s+ports\s+were/.test(lines[i+1].trim())
        )) {
          i++
          if (lines[i].trim() !== '') {
            consoleLines.push(lines[i].trim())
          }
        }
        processedLines.push({
          type: 'console',
          content: consoleLines.join('\n')
        })
        continue
      }

      processedLines.push({
        type: 'paragraph',
        content: trimmed
      })
    }

    return (
      <div className="space-y-3 font-sans text-xs text-slate-350 leading-relaxed">
        {processedLines.map((item, idx) => {
          if (item.type === 'empty') return <div key={idx} className="h-0.5" />
          if (item.type === 'divider') return <hr key={idx} className="border-slate-800/80 my-3" />

          if (item.type === 'header') {
            return (
              <h4 key={idx} className="text-xs font-bold text-white uppercase tracking-wider mt-5 mb-2.5 flex items-center gap-1.5">
                <span className="w-1 h-3.5 bg-primary-500 rounded-full" />
                <span>{item.content}</span>
              </h4>
            )
          }

          if (item.type === 'metadata') {
            return (
              <div key={idx} className="grid grid-cols-3 gap-2 py-1.5 border-b border-slate-800/40 text-[11px]">
                <span className="font-bold text-slate-500 uppercase tracking-wider">{item.key}</span>
                <span className="col-span-2 text-slate-200 font-sans">{parseBoldAndCode(item.value)}</span>
              </div>
            )
          }

          if (item.type === 'numbered-list') {
            return (
              <div key={idx} className="flex items-start space-x-2.5 pl-1 py-0.5">
                <span className="font-bold text-primary-400 shrink-0 min-w-[14px]">{item.number}.</span>
                <span className="text-slate-300">{parseBoldAndCode(item.content)}</span>
              </div>
            )
          }

          if (item.type === 'bullet-list') {
            return (
              <div key={idx} className="flex items-start space-x-2 pl-2.5 py-0.5">
                <span className="text-primary-500 shrink-0 mt-1">•</span>
                <span className="text-slate-350">{parseBoldAndCode(item.content)}</span>
              </div>
            )
          }

          if (item.type === 'code' || item.type === 'console') {
            return (
              <div key={idx} className="my-3 p-3.5 bg-slate-950/60 rounded-xl border border-slate-800/80 font-mono text-[10px] text-primary-300 overflow-x-auto whitespace-pre leading-normal">
                {item.content}
              </div>
            )
          }

          return (
            <p key={idx} className="text-slate-350">
              {parseBoldAndCode(item.content)}
            </p>
          )
        })}
      </div>
    )
  }

  const parseContent = (content: string) => {
    if (!content) return { description: 'No description provided.', recommendation: '', poc: '' }

    // Remove markdown title header
    let text = content.replace(/^#\s+.*$/m, '').trim()
    text = text.replace(/^\*\*ID:\*\*.*$/m, '')
    text = text.replace(/^\*\*Severity:\*\*.*$/m, '')
    text = text.replace(/^\*\*Found:\*\*.*$/m, '').trim()

    const sections = text.split(/##\s+/g)
    let description = ''
    let recommendation = ''
    let poc = ''

    sections.forEach(sec => {
      const lines = sec.trim().split('\n')
      const header = lines[0].toLowerCase().trim()
      const body = lines.slice(1).join('\n').trim()

      if (header.includes('description') || header.includes('overview')) {
        description = body
      } else if (header.includes('recommendation') || header.includes('remediation') || header.includes('mitigation') || header.includes('fix')) {
        recommendation = body
      } else if (header.includes('poc') || header.includes('proof of concept') || header.includes('exploit') || header.includes('proof')) {
        poc = body
      } else if (body) {
        description += `\n\n### ${lines[0]}\n${body}`
      }
    })

    if (!description && !recommendation && !poc) {
      description = text
    }

    return { description, recommendation, poc }
  }

  const { data, isLoading } = useQuery({
    queryKey: ['vulnerabilities'],
    queryFn: () => vulnerabilitiesAPI.getVulnerabilities().then(res => res.data),
    refetchInterval: 4000, // Refresh every 4 seconds for real-time parallel updates!
  })

  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-primary-500"></div>
      </div>
    )
  }

  const summary = data?.summary || { critical: 0, high: 0, medium: 0, low: 0 }
  const total = data?.total || 0

  const pieData = [
    { name: 'Critical', value: summary.critical, color: COLORS.critical },
    { name: 'High', value: summary.high, color: COLORS.high },
    { name: 'Medium', value: summary.medium, color: COLORS.medium },
    { name: 'Low', value: summary.low, color: COLORS.low },
  ].filter(item => item.value > 0)

  const barData = [
    { severity: 'Critical', count: summary.critical },
    { severity: 'High', count: summary.high },
    { severity: 'Medium', count: summary.medium },
    { severity: 'Low', count: summary.low },
  ]

  return (
    <div className="relative space-y-8 animate-in fade-in duration-700">
      {/* Background Overlay */}
      <div className="fixed inset-0 pointer-events-none overflow-hidden -z-10">
        <div className="absolute top-0 left-0 w-full h-full bg-gradient-to-br from-slate-900 via-transparent to-slate-900" />
        <div className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-full h-full bg-[radial-gradient(circle_at_center,rgba(220,38,38,0.03)_0%,transparent_70%)]" />
      </div>

      <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-6 pb-6 border-b border-slate-700/40">
        <div>
          <div className="flex items-center space-x-2 text-primary-500 mb-2">
            <Target className="h-5 w-5" />
            <span className="text-xs font-bold uppercase tracking-widest text-primary-400">Vulnerability Summary</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-bold text-white tracking-tight">Vulnerability <span className="text-primary-500">List</span></h1>
          <p className="text-slate-400 mt-1 max-w-xl">Comprehensive analysis of identified security weaknesses across all deployment nodes.</p>
        </div>
        <div className="flex items-center space-x-3">
          <div className="px-5 py-3 bg-primary-500/10 border border-primary-500/30 rounded-2xl shadow-lg shadow-slate-900/20">
            <p className="text-[10px] text-primary-400 font-bold uppercase tracking-widest mb-1">Total Exploits</p>
            <div className="flex items-baseline space-x-2">
              <span className="text-3xl font-bold text-white">{total}</span>
              <span className="text-xs font-bold text-primary-500/50 uppercase">Findings</span>
            </div>
          </div>
        </div>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {[
          { label: 'Critical', value: summary.critical, color: 'text-rose-500', bg: 'bg-rose-500/10', icon: AlertCircle, border: 'border-rose-500/20' },
          { label: 'High', value: summary.high, color: 'text-orange-500', bg: 'bg-orange-500/10', icon: AlertTriangle, border: 'border-orange-500/20' },
          { label: 'Medium', value: summary.medium, color: 'text-yellow-500', bg: 'bg-yellow-500/10', icon: Shield, border: 'border-yellow-500/20' },
          { label: 'Low', value: summary.low, color: 'text-sky-400', bg: 'bg-sky-400/10', icon: Activity, border: 'border-sky-400/20' },
        ].map((card) => (
          <div key={card.label} className={`group relative overflow-hidden rounded-2xl bg-slate-900/50 border ${card.border} p-6 transition-all duration-300 hover:scale-[1.02] hover:shadow-2xl`}>
            <div className={`absolute inset-0 ${card.bg} opacity-20 group-hover:opacity-40 transition-opacity`} />
            <div className="relative flex items-center justify-between">
              <div>
                <p className="text-[10px] font-bold text-slate-500 uppercase tracking-[0.2em] mb-1">{card.label}</p>
                <p className={`text-3xl font-bold ${card.color}`}>{card.value}</p>
              </div>
              <div className={`p-3 ${card.bg} rounded-2xl`}>
                <card.icon className={`h-6 w-6 ${card.color}`} />
              </div>
            </div>
            <div className={`absolute bottom-0 left-0 h-1 bg-gradient-to-r from-transparent via-${card.color.split('-')[1]}-${card.color.split('-')[2]} to-transparent w-full opacity-30`} />
          </div>
        ))}
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Distribution Chart */}
        <div className="group relative overflow-hidden rounded-[2.5rem] bg-slate-900/40 backdrop-blur-md border border-slate-800 p-6 shadow-2xl transition-all hover:border-slate-700/60">
          <div className="flex items-center justify-between mb-8">
            <h2 className="text-xl font-bold text-white uppercase tracking-tighter">Impact Distribution</h2>
            <div className="h-2 w-2 bg-primary-500 rounded-full " />
          </div>
          {total > 0 ? (
            <ResponsiveContainer width="100%" height={320}>
              <PieChart>
                <Pie
                  data={pieData}
                  cx="50%"
                  cy="50%"
                  innerRadius={60}
                  outerRadius={100}
                  paddingAngle={8}
                  dataKey="value"
                  stroke="none"
                >
                  {pieData.map((entry, index) => (
                    <Cell
                      key={`cell-${index}`}
                      fill={entry.color}
                      className="hover:opacity-80 transition-opacity cursor-pointer focus:outline-none"
                    />
                  ))}
                </Pie>
                <Tooltip
                  contentStyle={{
                    backgroundColor: '#0F172A',
                    border: '1px solid rgba(220,38,38,0.2)',
                    borderRadius: '16px',
                    color: '#F3F4F6',
                    fontSize: '12px',
                    fontWeight: 'bold',
                    textTransform: 'uppercase'
                  }}
                  itemStyle={{ color: '#EF4444' }}
                />
                <Legend
                  verticalAlign="bottom"
                  height={36}
                  formatter={(value) => <span className="text-[10px] font-bold text-slate-500 uppercase tracking-widest ml-1">{value}</span>}
                />
              </PieChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex flex-col items-center justify-center py-20 text-slate-600">
              <Shield className="h-12 w-12 mb-4 opacity-10" />
              <p className="text-sm font-bold uppercase tracking-widest">No active threats detected</p>
            </div>
          )}
        </div>

        {/* Magnitude Bar Chart */}
        <div className="group relative overflow-hidden rounded-[2.5rem] bg-slate-900/40 backdrop-blur-md border border-slate-800 p-6 shadow-2xl transition-all hover:border-slate-700/60">
          <div className="flex items-center justify-between mb-8">
            <h2 className="text-xl font-bold text-white uppercase tracking-tighter">Severity Magnitude</h2>
            <div className="p-2 bg-primary-500/10 rounded-lg"><Zap className="h-4 w-4 text-red-500" /></div>
          </div>
          {total > 0 ? (
            <ResponsiveContainer width="100%" height={320}>
              <BarChart data={barData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1E293B" vertical={false} />
                <XAxis
                  dataKey="severity"
                  stroke="#475569"
                  tick={{ fill: '#475569', fontSize: 10, fontWeight: 900 }}
                  axisLine={false}
                />
                <YAxis hide />
                <Tooltip
                  cursor={{ fill: 'rgba(220,38,38,0.05)' }}
                  contentStyle={{
                    backgroundColor: '#0F172A',
                    border: '1px solid rgba(220,38,38,0.2)',
                    borderRadius: '16px',
                    color: '#F3F4F6'
                  }}
                />
                <Bar dataKey="count" radius={[10, 10, 0, 0]} maxBarSize={50}>
                  {barData.map((entry, index) => (
                    <Cell key={`cell-${index}`} fill={COLORS[entry.severity.toLowerCase() as keyof typeof COLORS]} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="flex flex-col items-center justify-center py-20 text-slate-600">
              <Zap className="h-12 w-12 mb-4 opacity-10" />
              <p className="text-sm font-bold uppercase tracking-widest">Environment Secured</p>
            </div>
          )}
        </div>
      </div>

      {/* Vulnerability Ledger */}
      {data?.details && data.details.length > 0 && (
        <div className="relative overflow-hidden rounded-[2.5rem] bg-slate-900/50 backdrop-blur-md border border-slate-800 shadow-2xl shadow-black/50">
          <div className="p-6 border-b border-slate-800 bg-slate-950/20 flex items-center justify-between">
            <div className="flex items-center space-x-3">
              <div className="p-2 bg-primary-600 rounded-xl"><Activity className="h-5 w-5 text-white" /></div>
              <h2 className="text-xl font-bold text-white uppercase tracking-tighter">Identified Vulnerabilities</h2>
            </div>
            <span className="px-4 py-1.5 bg-slate-800 rounded-full text-[10px] font-bold text-slate-400 uppercase tracking-widest">
              {data.details.length} UNIQUE FINDINGS
            </span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left">
              <thead>
                <tr className="bg-slate-950/40 text-[10px] font-bold text-slate-500 uppercase tracking-[0.2em]">
                  <th className="py-5 px-8">Impact Level</th>
                  <th className="py-5 px-8">Payload Class</th>
                  <th className="py-5 px-8">Vulnerability Designation</th>
                  <th className="py-5 px-8">Origin Node</th>
                  <th className="py-5 px-8 text-right">Detection Lock</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-800/50">
                {data.details.map((detail: any, index: number) => {
                  const sev = (detail.severity || '').toLowerCase()
                  const uniqueRowId = `${detail.scan}_${detail.id || index}`
                  const isExpanded = expandedRow === uniqueRowId

                  return (
                    <Fragment key={uniqueRowId}>
                      <tr
                        onClick={() => setExpandedRow(isExpanded ? null : uniqueRowId)}
                        className={`group hover:bg-slate-800/40 transition-colors cursor-pointer select-none ${
                          isExpanded ? 'bg-slate-800/20' : ''
                        }`}
                      >
                        <td className="py-5 px-8">
                          <span className={`px-3 py-1.5 rounded-xl text-[10px] font-bold uppercase tracking-widest border ${
                            sev === 'critical' ? 'bg-rose-500/10 border-rose-500/30 text-rose-500' :
                            sev === 'high' ? 'bg-orange-500/10 border-orange-500/25 text-orange-500' :
                            sev === 'medium' ? 'bg-yellow-500/10 border-yellow-500/25 text-yellow-500' :
                            sev === 'low' ? 'bg-sky-500/10 border-sky-500/25 text-sky-400' :
                            'bg-slate-800 border-slate-700 text-slate-400'
                          }`}>
                            {sev.toUpperCase()}
                          </span>
                        </td>
                        <td className="py-5 px-8">
                          <code className="text-[10px] font-bold text-slate-400 bg-slate-950/40 px-2 py-1 rounded-lg border border-slate-700/40">
                            {detail.type || 'UNKNOWN'}
                          </code>
                        </td>
                        <td className="py-5 px-8">
                          <div className="flex items-center gap-2 text-sm font-bold text-white group-hover:text-slate-100 transition-colors uppercase tracking-tight">
                            {isExpanded ? (
                              <ChevronUp className="h-4 w-4 text-slate-400 flex-shrink-0" />
                            ) : (
                              <ChevronDown className="h-4 w-4 text-slate-400 flex-shrink-0" />
                            )}
                            <span>{detail.title || 'N/A'}</span>
                          </div>
                        </td>
                        <td className="py-5 px-8 text-[11px] font-mono text-slate-500 italic">
                          {detail.scan}
                        </td>
                        <td className="py-5 px-8 text-right text-[10px] font-bold text-slate-600 tracking-tighter">
                          {detail.timestamp ? new Date(detail.timestamp).toLocaleString() : 'N/A'}
                        </td>
                      </tr>

                      {isExpanded && (
                        <tr key={`${uniqueRowId}-detail`} className="bg-slate-950/15">
                          <td colSpan={5} className="py-6 px-8 border-t border-slate-800">
                            <div className="space-y-6 text-sm leading-relaxed animate-in slide-in-from-top-1 duration-200">
                              {(() => {
                                const { description, recommendation, poc } = parseContent(detail.content)
                                return (
                                  <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                                    {/* Description Box */}
                                    <div className="space-y-4 bg-slate-900/60 p-5 rounded-2xl border border-slate-800">
                                      <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2 mb-2">
                                        <FileText className="h-4.5 w-4.5 text-primary-400" />
                                        <span>Vulnerability Description</span>
                                      </h4>
                                      {renderFormattedMarkdown(description)}
                                    </div>

                                    {/* Recommendation Box */}
                                    {recommendation && (
                                      <div className="space-y-4 bg-emerald-950/10 p-5 rounded-2xl border border-emerald-500/20">
                                        <h4 className="text-xs font-bold text-emerald-400 uppercase tracking-wider flex items-center gap-2 mb-2">
                                          <Shield className="h-4.5 w-4.5 text-emerald-500" />
                                          <span>Remediation & Recommendation</span>
                                        </h4>
                                        {renderFormattedMarkdown(recommendation)}
                                      </div>
                                    )}

                                    {/* PoC Box */}
                                    {poc && (
                                      <div className="md:col-span-2 space-y-2 bg-slate-950/50 p-5 rounded-2xl border border-slate-850">
                                        <h4 className="text-xs font-bold text-slate-400 uppercase tracking-wider flex items-center gap-2">
                                          <Terminal className="h-4.5 w-4.5 text-primary-400" />
                                          <span>Technical Proof of Concept (PoC)</span>
                                        </h4>
                                        <pre className="text-slate-350 font-mono text-[11px] bg-black/35 p-4 rounded-xl overflow-x-auto whitespace-pre-wrap leading-relaxed">{poc}</pre>
                                      </div>
                                    )}

                                    {!recommendation && !poc && (
                                      <div className="md:col-span-2 text-xs text-slate-500 italic px-2">
                                        No further structured recommendation or exploit code provided in the log.
                                      </div>
                                    )}
                                  </div>
                                )
                              })()}
                            </div>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  )
                })}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  )
}

