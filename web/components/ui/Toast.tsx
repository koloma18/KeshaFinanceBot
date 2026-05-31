'use client';

import {
  createContext,
  useContext,
  useState,
  useCallback,
  useRef,
  ReactNode,
  useEffect,
} from 'react';

// ── Types ──

interface ToastItem {
  id: string;
  type: 'success' | 'error' | 'warning' | 'info';
  message: string;
}

interface ToastContextValue {
  showToast: (type: ToastItem['type'], message: string) => void;
}

const ToastContext = createContext<ToastContextValue | null>(null);

// ── Provider ──

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const timersRef = useRef<Map<string, ReturnType<typeof setTimeout>>>(new Map());

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
    const timer = timersRef.current.get(id);
    if (timer) {
      clearTimeout(timer);
      timersRef.current.delete(id);
    }
  }, []);

  const showToast = useCallback(
    (type: ToastItem['type'], message: string) => {
      const id = `${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
      setToasts((prev) => [...prev, { id, type, message }]);

      const timer = setTimeout(() => {
        removeToast(id);
      }, 3000);
      timersRef.current.set(id, timer);
    },
    [removeToast],
  );

  // Cleanup on unmount
  useEffect(() => {
    const timers = timersRef.current;
    return () => {
      timers.forEach((t) => clearTimeout(t));
      timers.clear();
    };
  }, []);

  return (
    <ToastContext.Provider value={{ showToast }}>
      {children}

      {/* Toast container */}
      <div
        aria-live="polite"
        className="fixed top-4 left-1/2 -translate-x-1/2 z-50 flex flex-col gap-2 w-full max-w-sm px-4 pointer-events-none"
      >
        {toasts.map((toast) => (
          <div
            key={toast.id}
            role="alert"
            onClick={() => removeToast(toast.id)}
            className={`
              pointer-events-auto cursor-pointer
              flex items-center gap-2 px-4 py-3 rounded-xl
              text-sm font-medium shadow-lg
              backdrop-blur-sm
              animate-toast-in
              ${toastBg(toast.type)}
              ${toastText(toast.type)}
            `}
          >
            <span className="shrink-0">{toastIcon(toast.type)}</span>
            <span>{toast.message}</span>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

// ── Hook ──

export function useToast(): ToastContextValue {
  const ctx = useContext(ToastContext);
  if (!ctx) {
    throw new Error('useToast must be used within a <ToastProvider>');
  }
  return ctx;
}

// ── Helpers ──

function toastIcon(type: ToastItem['type']): string {
  switch (type) {
    case 'success': return '✅';
    case 'error':   return '❌';
    case 'warning': return '⚠️';
    case 'info':    return 'ℹ️';
  }
}

function toastBg(type: ToastItem['type']): string {
  switch (type) {
    case 'success': return 'bg-emerald-950/90 border border-emerald-800/50';
    case 'error':   return 'bg-red-950/90 border border-red-800/50';
    case 'warning': return 'bg-amber-950/90 border border-amber-800/50';
    case 'info':    return 'bg-slate-900/90 border border-slate-700/50';
  }
}

function toastText(type: ToastItem['type']): string {
  switch (type) {
    case 'success': return 'text-emerald-200';
    case 'error':   return 'text-red-200';
    case 'warning': return 'text-amber-200';
    case 'info':    return 'text-slate-200';
  }
}
