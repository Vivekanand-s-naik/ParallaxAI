import * as React from 'react';
import { X } from 'lucide-react';
import { useUiStore } from '@/stores/ui-store';
import { cn } from '@/lib/utils';

export interface ContextualRightPanelProps {
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  className?: string;
}

/**
 * Optional Contextual Right Panel.
 * Only rendered on pages that explicitly provide contextual intelligence content.
 */
export function ContextualRightPanel({
  title,
  subtitle,
  children,
  className,
}: ContextualRightPanelProps) {
  const isOpen = useUiStore((s) => s.isRightPanelOpen);
  const setOpen = useUiStore((s) => s.setRightPanelOpen);

  if (!isOpen) return null;

  return (
    <aside
      aria-label={title}
      data-testid="contextual-right-panel"
      className={cn(
        'w-80 shrink-0 border-l border-border bg-card/70 p-4 xl:w-96',
        className
      )}
    >
      <div className="mb-4 flex items-start justify-between gap-2 border-b border-border pb-3">
        <div>
          <h2 className="text-xs font-semibold uppercase tracking-wider text-foreground">
            {title}
          </h2>
          {subtitle && (
            <p className="mt-0.5 text-xs text-muted-foreground">{subtitle}</p>
          )}
        </div>
        <button
          type="button"
          aria-label="Close contextual panel"
          onClick={() => setOpen(false)}
          className="rounded p-1 text-muted-foreground hover:bg-accent hover:text-foreground"
        >
          <X className="h-4 w-4" />
        </button>
      </div>
      <div className="space-y-4">{children}</div>
    </aside>
  );
}

