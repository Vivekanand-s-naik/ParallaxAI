import { Badge, type BadgeProps } from '@/components/ui/badge';
import { cn } from '@/lib/utils';

export type GovernanceStatusKey =
  | 'approved'
  | 'compliant'
  | 'healthy'
  | 'connected'
  | 'accept'
  | 'low'
  | 'pending'
  | 'under_review'
  | 'connecting'
  | 'reconnecting'
  | 'medium'
  | 'abstain'
  | 'rejected'
  | 'escalated'
  | 'non_compliant'
  | 'critical'
  | 'high'
  | 'reject'
  | 'disconnected'
  | 'unavailable'
  | (string & {});

const STATUS_VARIANT_MAP: Record<string, BadgeProps['variant']> = {
  approved: 'success',
  compliant: 'success',
  healthy: 'success',
  connected: 'success',
  accept: 'success',
  low: 'success',
  active: 'success',

  pending: 'warning',
  under_review: 'warning',
  connecting: 'warning',
  reconnecting: 'warning',
  medium: 'warning',
  abstain: 'warning',
  divided: 'warning',

  rejected: 'destructive',
  escalated: 'destructive',
  non_compliant: 'destructive',
  critical: 'destructive',
  high: 'destructive',
  reject: 'destructive',

  disconnected: 'outline',
  unavailable: 'outline',
  inactive: 'outline',
};

export interface StatusBadgeProps {
  status: GovernanceStatusKey;
  label?: string;
  showDot?: boolean;
  className?: string;
}

export function StatusBadge({
  status,
  label,
  showDot = true,
  className,
}: StatusBadgeProps) {
  const normalized = String(status).toLowerCase().trim();
  const variant = STATUS_VARIANT_MAP[normalized] ?? 'info';
  const displayLabel =
    label ?? normalized.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

  return (
    <Badge variant={variant} className={cn('font-medium', className)}>
      {showDot && (
        <span
          aria-hidden="true"
          className={cn(
            'h-1.5 w-1.5 rounded-full',
            variant === 'success' && 'bg-emerald-400',
            variant === 'warning' && 'bg-amber-400',
            variant === 'destructive' && 'bg-red-400',
            variant === 'info' && 'bg-sky-400',
            variant === 'default' && 'bg-primary',
            variant === 'outline' && 'bg-muted-foreground'
          )}
        />
      )}
      <span>{displayLabel}</span>
    </Badge>
  );
}
