import type { LucideIcon } from 'lucide-react';
import { Clock, Layers, ShieldCheck } from 'lucide-react';
import { PageHeader } from '@/components/common/page-header';
import { StatusBadge } from '@/components/common/status-badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import type { PermissionCode } from '@/types/auth';

export interface ModulePlaceholderProps {
  title: string;
  description: string;
  phaseLabel: string;
  endpointContract: string;
  requiredPermissions?: PermissionCode[];
  capabilities: string[];
  icon?: LucideIcon;
}

export function ModulePlaceholder({
  title,
  description,
  phaseLabel,
  endpointContract,
  requiredPermissions = [],
  capabilities,
  icon: Icon = Layers,
}: ModulePlaceholderProps) {
  return (
    <div className="space-y-6">
      <PageHeader
        title={title}
        description={description}
        badge={
          <StatusBadge
            status="pending"
            label={`Scheduled: ${phaseLabel}`}
          />
        }
      />

      <Card className="border-border/80 bg-card/80">
        <CardHeader className="pb-3">
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-primary/30 bg-primary/15 text-primary">
              <Icon className="h-5 w-5" aria-hidden="true" />
            </div>
            <div>
              <CardTitle>Development Architecture Placeholder</CardTitle>
              <p className="mt-1 text-xs text-muted-foreground">
                No fabricated metrics or simulated records are displayed during
                Phase 6. Live PostgreSQL data binding is scheduled for{' '}
                <span className="font-semibold text-foreground">
                  {phaseLabel}
                </span>
                .
              </p>
            </div>
          </div>
        </CardHeader>

        <CardContent className="grid gap-4 pt-2 md:grid-cols-2">
          <div className="rounded-md border border-border bg-background/60 p-4">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              <Clock className="h-3.5 w-3.5 text-primary" />
              <span>Planned Module Capabilities</span>
            </div>
            <ul className="mt-3 space-y-2 text-xs text-foreground/90">
              {capabilities.map((cap) => (
                <li key={cap} className="flex items-start gap-2">
                  <span
                    aria-hidden="true"
                    className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-primary"
                  />
                  <span>{cap}</span>
                </li>
              ))}
            </ul>
          </div>

          <div className="space-y-3 rounded-md border border-border bg-background/60 p-4">
            <div className="flex items-center gap-2 text-xs font-semibold uppercase tracking-wider text-muted-foreground">
              <ShieldCheck className="h-3.5 w-3.5 text-secondary" />
              <span>Verified Backend Contract</span>
            </div>
            <div className="space-y-2 text-xs">
              <div>
                <span className="text-muted-foreground">API Endpoint: </span>
                <code className="rounded bg-muted px-1.5 py-0.5 font-mono text-[11px] text-primary">
                  {endpointContract}
                </code>
              </div>
              <div>
                <span className="text-muted-foreground">
                  Required Permissions:{' '}
                </span>
                {requiredPermissions.length === 0 ? (
                  <span className="font-mono text-[11px] text-foreground">
                    Authenticated Session
                  </span>
                ) : (
                  <div className="mt-1.5 flex flex-wrap gap-1.5">
                    {requiredPermissions.map((perm) => (
                      <code
                        key={perm}
                        className="rounded border border-border bg-muted/60 px-2 py-0.5 font-mono text-[11px] text-foreground"
                      >
                        {perm}
                      </code>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

