import { Link } from 'react-router-dom';
import { Compass, ShieldAlert } from 'lucide-react';
import { Button } from '@/components/ui/button';

export function UnauthorizedPage() {
  return (
    <div
      data-testid="unauthorized-page"
      className="flex min-h-[65vh] flex-col items-center justify-center rounded-lg border border-amber-500/30 bg-amber-500/5 px-6 py-12 text-center"
    >
      <div className="flex h-12 w-12 items-center justify-center rounded-full border border-amber-500/40 bg-amber-500/15 text-amber-300">
        <ShieldAlert className="h-6 w-6" aria-hidden="true" />
      </div>
      <h1 className="mt-4 text-lg font-semibold text-foreground">
        Insufficient Governance Permissions
      </h1>
      <p className="mt-1.5 max-w-md text-xs text-muted-foreground">
        Your current operator role does not grant access to this governance
        module. Contact a Governance Officer or Super Administrator if you
        require elevated permissions.
      </p>
      <Button asChild variant="outline" size="sm" className="mt-5">
        <Link to="/app/dashboard">Return to Command Center</Link>
      </Button>
    </div>
  );
}

export function NotFoundPage() {
  return (
    <div
      data-testid="not-found-page"
      className="flex min-h-[70vh] flex-col items-center justify-center px-6 py-12 text-center"
    >
      <div className="flex h-12 w-12 items-center justify-center rounded-full border border-border bg-muted text-primary">
        <Compass className="h-6 w-6" aria-hidden="true" />
      </div>
      <p className="mt-3 font-mono text-xs font-semibold uppercase tracking-widest text-primary">
        HTTP 404 — Route Not Found
      </p>
      <h1 className="mt-1 text-xl font-semibold text-foreground">
        Requested Governance Route Does Not Exist
      </h1>
      <p className="mt-1.5 max-w-md text-xs text-muted-foreground">
        The URL you navigated to is not registered in the ParallaxAI Command
        Center router.
      </p>
      <Button asChild variant="default" size="sm" className="mt-5">
        <Link to="/app/dashboard">Go to Command Center</Link>
      </Button>
    </div>
  );
}

