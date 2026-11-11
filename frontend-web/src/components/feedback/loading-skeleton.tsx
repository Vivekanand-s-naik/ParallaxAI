import { Skeleton } from '@/components/ui/skeleton';
import { cn } from '@/lib/utils';

export interface LoadingSkeletonProps {
  cards?: number;
  rows?: number;
  className?: string;
}

export function LoadingSkeleton({
  cards = 4,
  rows = 4,
  className,
}: LoadingSkeletonProps) {
  return (
    <div
      aria-busy="true"
      aria-label="Loading workspace content"
      className={cn('space-y-6', className)}
    >
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {Array.from({ length: cards }).map((_, idx) => (
          <Skeleton key={idx} className="h-24 w-full rounded-lg" />
        ))}
      </div>
      <div className="space-y-3 rounded-lg border border-border bg-card p-5">
        {Array.from({ length: rows }).map((_, idx) => (
          <Skeleton key={idx} className="h-10 w-full" />
        ))}
      </div>
    </div>
  );
}

