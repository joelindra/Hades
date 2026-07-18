import React, { createContext, useContext, useState, useCallback, ReactNode } from 'react'
import { CheckCircle, XCircle, Info, X } from 'lucide-react'

type ToastType = 'success' | 'error' | 'info'

interface Toast {
    id: string
    message: string
    type: ToastType
}

interface ToastContextType {
    showToast: (message: string, type?: ToastType) => void
}

const ToastContext = createContext<ToastContextType | undefined>(undefined)

export const useToast = () => {
    const context = useContext(ToastContext)
    if (!context) {
        throw new Error('useToast must be used within a ToastProvider')
    }
    return context
}

interface ToastProviderProps {
    children: ReactNode
}

export const ToastProvider: React.FC<ToastProviderProps> = ({ children }) => {
    const [toasts, setToasts] = useState<Toast[]>([])

    const showToast = useCallback((message: string, type: ToastType = 'info') => {
        const id = Math.random().toString(36).substring(2, 9)
        setToasts((prev) => [...prev, { id, message, type }])

        // Auto remove after 5 seconds
        setTimeout(() => {
            setToasts((prev) => prev.filter((t) => t.id !== id))
        }, 5000)
    }, [])

    const removeToast = (id: string) => {
        setToasts((prev) => prev.filter((t) => t.id !== id))
    }

    return (
        <ToastContext.Provider value={{ showToast }}>
            {children}
            <div className="fixed bottom-4 right-4 z-[9999] flex flex-col space-y-3 pointer-events-none">
                {toasts.map((toast) => (
                    <div
                        key={toast.id}
                        className={`
              flex items-center space-x-3 px-4 py-3 rounded-xl border shadow-2xl animate-slide-in-right pointer-events-auto min-w-[300px] max-w-md
              ${toast.type === 'success' ? 'bg-emerald-950/90 border-emerald-500/50 text-emerald-100' : ''}
              ${toast.type === 'error' ? 'bg-red-950/90 border-red-500/50 text-red-100' : ''}
              ${toast.type === 'info' ? 'bg-slate-900/90 border-primary-500/50 text-primary-100' : ''}
              backdrop-blur-md
            `}
                    >
                        <div className="flex-shrink-0">
                            {toast.type === 'success' && <CheckCircle className="h-5 w-5 text-emerald-400" />}
                            {toast.type === 'error' && <XCircle className="h-5 w-5 text-red-400" />}
                            {toast.type === 'info' && <Info className="h-5 w-5 text-primary-400" />}
                        </div>
                        <div className="flex-1 text-sm font-medium">
                            {toast.message}
                        </div>
                        <button
                            onClick={() => removeToast(toast.id)}
                            className="flex-shrink-0 hover:bg-white/10 rounded-lg p-1 transition-colors"
                        >
                            <X className="h-4 w-4 opacity-70" />
                        </button>
                    </div>
                ))}
            </div>
        </ToastContext.Provider>
    )
}
