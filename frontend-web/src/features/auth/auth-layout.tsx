import * as React from 'react';
import {
  FileCheck2,
  Layers,
  LockKeyhole,
  Scale,
  ShieldCheck,
} from 'lucide-react';
import { ToastViewport } from '@/components/feedback/toast-viewport';

export interface AuthLayoutProps {
  title: string;
  subtitle: string;
  children: React.ReactNode;
  footer?: React.ReactNode;
}

const GOVERNANCE_PILLARS = [
  {
    icon: ShieldCheck,
    title: 'Multi-Agent Consensus & Human Oversight',
    description:
      'Collaboratively evaluate high-stakes decisions across AI models and authorized human reviewers with weighted influence.',
  },
  {
    icon: Scale,
    title: 'Real-Time Bias & Fairness Telemetry',
    description:
      'Continuous demographic parity, equal opportunity, and ML anomaly scanning on every decision record.',
  },
  {
    icon: FileCheck2,
    title: 'Tamper-Evident SHA-256 Audit Trail',
    description:
      'Every vote, policy evaluation, escalation, and status transition is cryptographically hashed in PostgreSQL.',
  },
];

export function AuthLayout({
  title,
  subtitle,
  children,
  footer,
}: AuthLayoutProps) {
  return (
    <div className="grid min-h-screen w-full bg-background text-foreground lg:grid-cols-12">
      {/* Left Enterprise Governance Identity Panel */}
      <div className="hidden flex-col justify-between border-r border-sidebar-border bg-sidebar p-10 lg:col-span-5 lg:flex xl:p-12">
        <div>
          <div className="flex items-center gap-3">
            <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-primary/40 bg-primary/15 text-primary">
              <Layers className="h-5 w-5" />
            </div>
            <div>
              <span className="text-base font-bold tracking-wider text-foreground">
                PARALLAXAI
              </span>
              <p className="text-[10px] font-semibold uppercase tracking-widest text-primary">
                AI GOVERNANCE COMMAND CENTER
              </p>
            </div>
          </div>

          <div className="mt-12 space-y-3">
            <h1 className="text-2xl font-semibold leading-tight tracking-tight text-foreground">
              Transparent, Fair & Accountable Human-AI Co-Governance
            </h1>
            <p className="text-sm leading-relaxed text-muted-foreground">
              Enterprise command plane for collaborative decision evaluation,
              multi-agent voting, YAML policy enforcement, and regulatory
              auditability.
            </p>
          </div>

          <div className="mt-10 space-y-5">
            {GOVERNANCE_PILLARS.map((pillar) => {
              const Icon = pillar.icon;
              return (
                <div
                  key={pillar.title}
                  className="flex items-start gap-3.5 rounded-lg border border-sidebar-border bg-card/40 p-4"
                >
                  <div className="mt-0.5 flex h-8 w-8 shrink-0 items-center justify-center rounded-md border border-primary/30 bg-primary/10 text-primary">
                    <Icon className="h-4 w-4" aria-hidden="true" />
                  </div>
                  <div className="space-y-1">
                    <h2 className="text-xs font-semibold text-foreground">
                      {pillar.title}
                    </h2>
                    <p className="text-xs leading-relaxed text-muted-foreground">
                      {pillar.description}
                    </p>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        <div className="flex items-center justify-between border-t border-sidebar-border pt-6 text-xs text-muted-foreground">
          <div className="flex items-center gap-2">
            <LockKeyhole className="h-3.5 w-3.5 text-primary" />
            <span>Argon2id + JWT Session Rotation + RBAC</span>
          </div>
          <span className="font-mono text-[11px]">v2.0</span>
        </div>
      </div>

      {/* Right Authentication Form Workspace */}
      <div className="flex flex-col items-center justify-center px-4 py-10 sm:px-8 lg:col-span-7">
        {/* Mobile Brand Header */}
        <div className="mb-8 flex items-center gap-3 lg:hidden">
          <div className="flex h-9 w-9 items-center justify-center rounded-lg border border-primary/40 bg-primary/15 text-primary">
            <Layers className="h-5 w-5" />
          </div>
          <div>
            <p className="text-sm font-bold tracking-wider">PARALLAXAI</p>
            <p className="text-[10px] font-medium tracking-widest text-muted-foreground">
              AI GOVERNANCE COMMAND CENTER
            </p>
          </div>
        </div>

        <div className="w-full max-w-md space-y-6">
          <div className="rounded-xl border border-border bg-card p-6 shadow-lg sm:p-8">
            <div className="mb-6 space-y-1.5">
              <h2 className="text-xl font-semibold tracking-tight text-foreground">
                {title}
              </h2>
              <p className="text-xs text-muted-foreground">{subtitle}</p>
            </div>

            {children}
          </div>

          {footer && (
            <div className="text-center text-xs text-muted-foreground">
              {footer}
            </div>
          )}
        </div>
      </div>

      <ToastViewport />
    </div>
  );
}

