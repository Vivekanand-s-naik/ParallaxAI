import { AlertCircle, CheckCircle2, Info, X } from 'lucide-react';
import { useUiStore } from '@/stores/ui-store';
import { cn } from '@/lib/utils';

export function ToastViewport() {
  const toasts = useUiStore((s) => s.toasts);
  const dismissToast = useUiStore((s) => s.dismissToast);

  if (toasts.length === 0) return null;

  return (
    <div
      aria-live="polite"
      aria-label="System notifications"
      className="fixed bottom-4 right-4 z-50 flex w-full max-w-sm flex-col gap-2 px-4 sm:px-0"
    >
      {toasts.map((toast) => (
        <div
          key={toast.id}
          role="status"
          className={cn(
            'flex items-start gap-3 rounded-lg border bg-popover p-3.5 text-popover-foreground shadow-lg',
            toast.variant === 'success' && 'border-emerald-500/40',
            toast.variant === 'warning' && 'border-amber-500/40',
            toast.variant === 'error' && 'border-red-500/40',
            toast.variant === 'info' && 'border-primary/40'
          )}
        >
          {toast.variant === 'success' && (
            <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" />
          )}
          {(toast.variant === 'warning' || toast.variant === 'error') && (
            <AlertCircle
              className={cn(
                'mt-0.5 h-4 w-4 shrink-0',
                toast.variant === 'warning' ? 'text-amber-400' : 'text-red-400'
              )}
            />
          )}
          {toast.variant === 'info' && (
            <Info className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
          )}
          <div className="flex-1 text-xs">
            <p className="font-semibold text-foreground">{toast.title}</p>
            {toast.description && (
              <p className="mt-0.5 text-muted-foreground">
                {toast.description}
              </p>
            )}
          </div>
          <button
            type="button"
            aria-label="Dismiss notification"
            onClick={() => dismissToast(toast.id)}
            className="rounded p-0.5 text-muted-foreground hover:bg-accent hover:text-foreground"
          >
            <X className="h-3.5 w-3.5" />
          </button>
        </div>
      ))}
    </div>
  );
}

