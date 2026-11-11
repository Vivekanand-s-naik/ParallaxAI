import * as React from 'react';
import type { LucideIcon } from 'lucide-react';
import { Card, CardContent } from '@/components/ui/card';
import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';

export interface StatCardProps {
  label: string;
  value: React.ReactNode;
  sublabel?: string;
  icon?: LucideIcon;
  tone?: 'default' | 'primary' | 'secondary' | 'success' | 'warning' | 'critical';
  isLoading?: boolean;
  className?: string;
}

const TONE_ICON_STYLES: Record<NonNullable<StatCardProps['tone']>, string> = {
  default: 'bg-muted text-muted-foreground border-border',
  primary: 'bg-primary/15 text-primary border-primary/30',
  secondary: 'bg-secondary/15 text-secondary border-secondary/30',
  success: 'bg-emerald-500/15 text-emerald-300 border-emerald-500/30',
  warning: 'bg-amber-500/15 text-amber-300 border-amber-500/30',
  critical: 'bg-red-500/15 text-red-300 border-red-500/30',
};

export function StatCard({
  label,
  value,
  sublabel,
  icon: Icon,
  tone = 'default',
  isLoading = false,
  className,
}: StatCardProps) {
  return (
    <Card className={cn('border-border/80 bg-card/90', className)}>
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-3">
          <div className="space-y-1.5">
            <p className="text-xs font-medium uppercase tracking-wider text-muted-foreground">
              {label}
            </p>
            {isLoading ? (
              <Skeleton className="h-7 w-20" />
            ) : (
              <div className="font-mono text-2xl font-semibold tracking-tight text-foreground">
                {value}
              </div>
            )}
            {sublabel && (
              <p className="text-xs text-muted-foreground">{sublabel}</p>
            )}
          </div>
          {Icon && (
            <div
              className={cn(
                'flex h-9 w-9 shrink-0 items-center justify-center rounded-md border',
                TONE_ICON_STYLES[tone]
              )}
            >
              <Icon className="h-4 w-4" aria-hidden="true" />
            </div>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
