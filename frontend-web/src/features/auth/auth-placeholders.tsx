import { Link } from 'react-router-dom';
import { Layers, Lock } from 'lucide-react';
import { StatusBadge } from '@/components/common/status-badge';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';

export function LoginPagePlaceholder() {
  return (
    <AuthScreenShell
      title="Operator Sign In"
      subtitle="Authenticate with the ParallaxAI Governance Command Center."
      endpoint="POST /api/v1/auth/login"
      footerLink={{ to: '/register', label: 'Create a governance observer account' }}
    />
  );
}

export function RegisterPagePlaceholder() {
  return (
    <AuthScreenShell
      title="Operator Registration"
      subtitle="Provision a new ParallaxAI account with default VIEWER governance access."
      endpoint="POST /api/v1/auth/register"
      footerLink={{ to: '/login', label: 'Return to Operator Sign In' }}
    />
  );
}

export function ForgotPasswordPagePlaceholder() {
  return (
    <AuthScreenShell
      title="Credential Recovery"
      subtitle="Request a password reset token. Outbound email status is verified from the backend."
      endpoint="POST /api/v1/auth/forgot-password"
      footerLink={{ to: '/login', label: 'Return to Operator Sign In' }}
    />
  );
}

function AuthScreenShell({
  title,
  subtitle,
  endpoint,
  footerLink,
}: {
  title: string;
  subtitle: string;
  endpoint: string;
  footerLink: { to: string; label: string };
}) {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-background px-4 py-12 text-foreground">
      <div className="mb-6 flex items-center gap-3">
        <div className="flex h-10 w-10 items-center justify-center rounded-lg border border-primary/40 bg-primary/15 text-primary">
          <Layers className="h-5 w-5" />
        </div>
        <div>
          <p className="text-sm font-bold tracking-wider">PARALLAXAI</p>
          <p className="text-[10px] font-medium tracking-widest text-muted-foreground">
            AI GOVERNANCE COMMAND CENTER
          </p>
        </div>
      </div>

      <Card className="w-full max-w-md border-border bg-card">
        <CardHeader>
          <div className="flex items-center justify-between">
            <CardTitle>{title}</CardTitle>
            <StatusBadge status="pending" label="Phase 7 UI" />
          </div>
          <p className="mt-1 text-xs text-muted-foreground">{subtitle}</p>
        </CardHeader>
        <CardContent className="space-y-4 text-xs">
          <div className="rounded-md border border-border bg-background/70 p-3.5">
            <div className="flex items-center gap-2 font-semibold text-foreground">
              <Lock className="h-3.5 w-3.5 text-primary" />
              <span>Phase 7 Authentication Workflow Placeholder</span>
            </div>
            <p className="mt-1.5 text-muted-foreground">
              Interactive React Hook Form + Zod validation, Argon2id session
              submission, and honest Google OAuth 2.0 state handling will be
              connected in Phase 7 against{' '}
              <code className="font-mono text-primary">{endpoint}</code>.
            </p>
          </div>
          <div className="flex items-center justify-between border-t border-border pt-3">
            <Link to={footerLink.to} className="text-primary hover:underline">
              {footerLink.label}
            </Link>
            <Link
              to="/forgot-password"
              className="text-muted-foreground hover:text-foreground"
            >
              Forgot password?
            </Link>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

