import { create } from 'zustand';

export type ToastType = 'success' | 'error' | 'warning' | 'info';

export interface ToastItem {
  id: string;
  type: ToastType;
  message: string;
}

interface ToastStore {
  toasts: ToastItem[];
  queue: ToastItem[];
  addToast: (type: ToastType, message: string) => void;
  removeToast: (id: string) => void;
}

export const useToastStore = create<ToastStore>((set, get) => ({
  toasts: [],
  queue: [],
  addToast: (type, message) => {
    const id = Math.random().toString(36).substring(2, 9);
    const newToast = { id, type, message };
    const { toasts, queue } = get();
    
    if (toasts.length < 3) {
      set({ toasts: [...toasts, newToast] });
    } else {
      set({ queue: [...queue, newToast] });
    }
  },
  removeToast: (id) => {
    const { toasts, queue } = get();
    const filteredToasts = toasts.filter((t) => t.id !== id);
    
    if (queue.length > 0 && filteredToasts.length < 3) {
      const next = queue[0];
      set({
        toasts: [...filteredToasts, next],
        queue: queue.slice(1)
      });
    } else {
      set({ toasts: filteredToasts });
    }
  }
}));

export const toast = {
  success: (msg: string) => useToastStore.getState().addToast('success', msg),
  error: (msg: string) => useToastStore.getState().addToast('error', msg),
  warning: (msg: string) => useToastStore.getState().addToast('warning', msg),
  info: (msg: string) => useToastStore.getState().addToast('info', msg),
};
export default toast;
