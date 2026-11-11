import * as React from 'react';
import { ShieldAlert, RotateCcw } from 'lucide-react';
import { Button } from '@/components/ui/button';

interface ErrorBoundaryState {
  hasError: boolean;
  errorMessage: string;
}

export class AppErrorBoundary extends React.Component<
  { children: React.ReactNode },
  ErrorBoundaryState
> {
  constructor(props: { children: React.ReactNode }) {
    super(props);
    this.state = { hasError: false, errorMessage: '' };
  }

  static getDerivedStateFromError(error: Error): ErrorBoundaryState {
    return {
      hasError: true,
      errorMessage:
        error?.message || 'An unexpected UI error occurred in the workspace.',
    };
  }

  handleReset = () => {
    this.setState({ hasError: false, errorMessage: '' });
  };

  render() {
    if (this.state.hasError) {
      return (
        <div
          role="alert"
          className="flex min-h-screen flex-col items-center justify-center bg-background px-6 text-center text-foreground"
        >
          <div className="flex h-12 w-12 items-center justify-center rounded-full border border-red-500/30 bg-red-500/15 text-red-400">
            <ShieldAlert className="h-6 w-6" />
          </div>
          <h1 className="mt-4 text-lg font-semibold">
            Workspace Rendering Interrupted
          </h1>
          <p className="mt-1.5 max-w-md text-sm text-muted-foreground">
            {this.state.errorMessage}
          </p>
          <Button
            variant="outline"
            size="sm"
            onClick={this.handleReset}
            className="mt-5"
          >
            <RotateCcw className="h-4 w-4" />
            Reload Workspace View
          </Button>
        </div>
      );
    }

    return this.props.children;
  }
}
