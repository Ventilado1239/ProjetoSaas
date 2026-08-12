import React, { useEffect } from 'react';
import { useToastStore } from '../services/toast';
import type { ToastItem } from '../services/toast';
import { CheckCircle2, AlertTriangle, AlertCircle, Info, X } from 'lucide-react';

const Toast: React.FC<{ toast: ToastItem }> = ({ toast }) => {
  const removeToast = useToastStore((state) => state.removeToast);

  useEffect(() => {
    const timer = setTimeout(() => {
      removeToast(toast.id);
    }, 4000);
    return () => clearTimeout(timer);
  }, [toast.id, removeToast]);

  const getStyleClass = () => {
    switch (toast.type) {
      case 'success':
        return 'bg-emerald-50 border-emerald-200/60 text-emerald-800';
      case 'error':
        return 'bg-rose-50 border-rose-200/60 text-rose-800';
      case 'warning':
        return 'bg-amber-50 border-amber-200/60 text-amber-800';
      case 'info':
        return 'bg-blue-50 border-blue-200/60 text-blue-800';
    }
  };

  const getIcon = () => {
    switch (toast.type) {
      case 'success':
        return <CheckCircle2 size={16} className="text-success shrink-0" />;
      case 'error':
        return <AlertCircle size={16} className="text-danger shrink-0" />;
      case 'warning':
        return <AlertTriangle size={16} className="text-warning shrink-0" />;
      case 'info':
        return <Info size={16} className="text-accent shrink-0" />;
    }
  };

  return (
    <div
      className={`flex items-center justify-between gap-3 px-4 py-3 border rounded-large shadow-md transition-all duration-200 w-[90vw] sm:w-[350px] animate-fade-in ${getStyleClass()}`}
    >
      <div className="flex items-center gap-2.5 min-w-0">
        {getIcon()}
        <span className="text-xs font-semibold truncate leading-none">{toast.message}</span>
      </div>
      <button
        onClick={() => removeToast(toast.id)}
        className="p-1 hover:bg-black/5 rounded-full text-text-secondary cursor-pointer shrink-0 transition-colors"
        aria-label="Fechar"
      >
        <X size={14} />
      </button>
    </div>
  );
};

export const ToastContainer: React.FC = () => {
  const toasts = useToastStore((state) => state.toasts);

  return (
    <div className="fixed bottom-[calc(76px+env(safe-area-inset-bottom))] left-1/2 -translate-x-1/2 sm:bottom-auto sm:top-4 sm:left-auto sm:translate-x-0 sm:right-4 z-[9999] flex flex-col gap-2 max-w-full">
      {toasts.map((t) => (
        <Toast key={t.id} toast={t} />
      ))}
    </div>
  );
};
export default ToastContainer;
