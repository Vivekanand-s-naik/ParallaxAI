import { create } from 'zustand';
import type { WebSocketConnectionState } from '@/types/navigation';

export type ToastVariant = 'info' | 'success' | 'warning' | 'error';

export interface ToastMessage {
  id: string;
  title: string;
  description?: string;
  variant: ToastVariant;
}

const SIDEBAR_STORAGE_KEY = 'parallaxai_sidebar_collapsed';

function readInitialSidebarCollapsed(): boolean {
  try {
    if (typeof window === 'undefined' || !window.localStorage) return false;
    return window.localStorage.getItem(SIDEBAR_STORAGE_KEY) === 'true';
  } catch {
    return false;
  }
}

function writeSidebarCollapsed(collapsed: boolean): void {
  try {
    if (typeof window !== 'undefined' && window.localStorage) {
      window.localStorage.setItem(SIDEBAR_STORAGE_KEY, String(collapsed));
    }
  } catch {
    // Ignore storage quota / privacy mode errors
  }
}

interface UiState {
  isSidebarCollapsed: boolean;
  isMobileSidebarOpen: boolean;
  isCommandSearchOpen: boolean;
  isRightPanelOpen: boolean;
  wsConnectionState: WebSocketConnectionState;
  toasts: ToastMessage[];
  toggleSidebar: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  setMobileSidebarOpen: (open: boolean) => void;
  setCommandSearchOpen: (open: boolean) => void;
  setRightPanelOpen: (open: boolean) => void;
  setWsConnectionState: (state: WebSocketConnectionState) => void;
  addToast: (toast: Omit<ToastMessage, 'id'>) => string;
  dismissToast: (id: string) => void;
}

export const useUiStore = create<UiState>((set) => ({
  isSidebarCollapsed: readInitialSidebarCollapsed(),
  isMobileSidebarOpen: false,
  isCommandSearchOpen: false,
  isRightPanelOpen: false,
  // Honest default state in Phase 6 until Phase 11 WebSocket client is active
  wsConnectionState: 'disconnected',
  toasts: [],

  toggleSidebar: () =>
    set((state) => {
      const next = !state.isSidebarCollapsed;
      writeSidebarCollapsed(next);
      return { isSidebarCollapsed: next };
    }),

  setSidebarCollapsed: (collapsed) => {
    writeSidebarCollapsed(collapsed);
    set({ isSidebarCollapsed: collapsed });
  },

  setMobileSidebarOpen: (open) => set({ isMobileSidebarOpen: open }),

  setCommandSearchOpen: (open) => set({ isCommandSearchOpen: open }),

  setRightPanelOpen: (open) => set({ isRightPanelOpen: open }),

  setWsConnectionState: (wsConnectionState) => set({ wsConnectionState }),

  addToast: (toast) => {
    const id = `toast_${Date.now()}_${Math.random().toString(36).slice(2, 7)}`;
    set((state) => ({
      toasts: [...state.toasts.slice(-4), { ...toast, id }],
    }));
    return id;
  },

  dismissToast: (id) =>
    set((state) => ({
      toasts: state.toasts.filter((t) => t.id !== id),
    })),
}));
