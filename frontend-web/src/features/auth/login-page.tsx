import * as React from 'react';
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useQuery } from '@tanstack/react-query';
import {
  AlertCircle,
  Eye,
  EyeOff,
  Loader2,
  Lock,
  LogIn,
  ShieldAlert,
} from 'lucide-react';
import { queryKeys } from '@/app/query-client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { AuthLayout } from './auth-layout';
import { loginSchema, type LoginFormValues } from './auth-schemas';
import { authService } from '@/services/auth-service';
import { normalizeApiError } from '@/services/api-error';
import { useAuthStore } from '@/stores/auth-store';
import { useUiStore } from '@/stores/ui-store';

export function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const addToast = useUiStore((s) => s.addToast);

  const [showPassword, setShowPassword] = React.useState(false);
  const [submitError, setSubmitError] = React.useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  const redirectTarget =
    (location.state as { from?: string } | null)?.from || '/app/dashboard';

  const { data: providersStatus, isLoading: isProvidersLoading } = useQuery({
    queryKey: queryKeys.auth.providers(),
    queryFn: () => authService.getProvidersStatus(),
    staleTime: 60_000,
  });

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormValues>({
    resolver: zodResolver(loginSchema),
    defaultValues: {
      identifier: '',
      password: '',
      remember_me: false,
    },
  });

  if (isAuthenticated) {
    return <Navigate to={redirectTarget} replace />;
  }

  const onSubmit = async (values: LoginFormValues) => {
    setSubmitError(null);
    setIsSubmitting(true);
    try {
      const response = await authService.login({
        identifier: values.identifier.trim(),
        password: values.password,
        remember_me: values.remember_me,
      });
      addToast({
        title: 'Authenticated with Command Center',
        description: `Signed in as ${response.user.full_name} (${response.user.role})`,
        variant: 'success',
      });
      navigate(redirectTarget, { replace: true });
    } catch (error) {
      const apiErr = normalizeApiError(error);
      setSubmitError(apiErr.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleGoogleSignIn = async () => {
    if (!providersStatus?.google_oauth_enabled) return;
    setSubmitError(null);
    try {
      const { authorization_url } = await authService.initiateGoogleOAuth(
        window.location.origin
      );
      window.location.assign(authorization_url);
    } catch (error) {
      const apiErr = normalizeApiError(error);
      setSubmitError(apiErr.message);
    }
  };

  const googleEnabled = Boolean(providersStatus?.google_oauth_enabled);

  return (
    <AuthLayout
      title="Operator Sign In"
      subtitle="Enter your governance credentials to access the ParallaxAI Command Center."
      footer={
        <span>
          New to the platform?{' '}
          <Link
            to="/register"
            className="font-semibold text-primary hover:underline"
          >
            Register an operator account
          </Link>
        </span>
      }
    >
      <form
        onSubmit={handleSubmit(onSubmit)}
        noValidate
        className="space-y-4"
        aria-label="Operator login form"
      >
        {submitError && (
          <div
            role="alert"
            data-testid="login-error-alert"
            className="flex items-start gap-2.5 rounded-md border border-red-500/40 bg-red-500/10 p-3 text-xs text-red-200"
          >
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-400" />
            <span>{submitError}</span>
          </div>
        )}

        {/* Email or Username Field */}
        <div className="space-y-1.5">
          <label
            htmlFor="login-identifier"
            className="block text-xs font-medium text-foreground"
          >
            Email or Username
          </label>
          <Input
            id="login-identifier"
            type="text"
            autoComplete="username"
            placeholder="admin@parallaxai.io or username"
            aria-invalid={Boolean(errors.identifier)}
            {...register('identifier')}
          />
          {errors.identifier && (
            <p
              role="alert"
              className="text-xs text-red-400"
            >
              {errors.identifier.message}
            </p>
          )}
        </div>

        {/* Password Field with Show/Hide toggle */}
        <div className="space-y-1.5">
          <div className="flex items-center justify-between">
            <label
              htmlFor="login-password"
              className="block text-xs font-medium text-foreground"
            >
              Password
            </label>
            <Link
              to="/forgot-password"
              className="text-xs font-medium text-primary hover:underline"
            >
              Forgot password?
            </Link>
          </div>
          <div className="relative">
            <Input
              id="login-password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="current-password"
              placeholder="Enter your password"
              aria-invalid={Boolean(errors.password)}
              className="pr-10"
              {...register('password')}
            />
            <button
              type="button"
              onClick={() => setShowPassword((prev) => !prev)}
              aria-label={showPassword ? 'Hide password' : 'Show password'}
              className="absolute right-2.5 top-2 rounded p-0.5 text-muted-foreground hover:text-foreground focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
            >
              {showPassword ? (
                <EyeOff className="h-4 w-4" />
              ) : (
                <Eye className="h-4 w-4" />
              )}
            </button>
          </div>
          {errors.password && (
            <p
              role="alert"
              className="text-xs text-red-400"
            >
              {errors.password.message}
            </p>
          )}
        </div>

        {/* Remember Me Checkbox */}
        <div className="flex items-center justify-between pt-0.5">
          <label
            htmlFor="login-remember-me"
            className="flex cursor-pointer items-center gap-2 text-xs text-muted-foreground select-none"
          >
            <input
              id="login-remember-me"
              type="checkbox"
              className="h-3.5 w-3.5 rounded border-border bg-background text-primary focus:ring-primary"
              {...register('remember_me')}
            />
            <span>Keep session active for 30 days</span>
          </label>
        </div>

        {/* Submit Button */}
        <Button
          type="submit"
          disabled={isSubmitting}
          className="w-full"
        >
          {isSubmitting ? (
            <>
              <Loader2 className="h-4 w-4 animate-spin" />
              <span>Authenticating…</span>
            </>
          ) : (
            <>
              <LogIn className="h-4 w-4" />
              <span>Sign In to Command Center</span>
            </>
          )}
        </Button>

        {/* Divider */}
        <div className="relative py-2">
          <div className="absolute inset-0 flex items-center">
            <span className="w-full border-t border-border" />
          </div>
          <div className="relative flex justify-center text-[11px] uppercase">
            <span className="bg-card px-2 text-muted-foreground">
              Federated Identity
            </span>
          </div>
        </div>

        {/* Honest Google Sign-In Placeholder */}
        <div className="space-y-2">
          <Button
            type="button"
            variant="outline"
            disabled={!googleEnabled || isProvidersLoading}
            onClick={handleGoogleSignIn}
            data-testid="google-oauth-button"
            className="w-full"
          >
            <Lock className="h-3.5 w-3.5 text-muted-foreground" />
            <span>
              {googleEnabled
                ? 'Continue with Google OAuth 2.0'
                : 'Continue with Google (Unavailable)'}
            </span>
          </Button>

          {!googleEnabled && (
            <div
              data-testid="google-oauth-unavailable-notice"
              className="flex items-start gap-2 rounded-md border border-border/80 bg-background/60 px-3 py-2 text-[11px] text-muted-foreground"
            >
              <ShieldAlert className="mt-0.5 h-3.5 w-3.5 shrink-0 text-amber-400" />
              <span>
                {providersStatus?.google_oauth_message ||
                  'Google Sign-In is disabled until GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, and GOOGLE_REDIRECT_URI are configured on the server.'}
              </span>
            </div>
          )}
        </div>
      </form>
    </AuthLayout>
  );
}

