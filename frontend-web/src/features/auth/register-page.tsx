import * as React from 'react';
import { Link, Navigate, useNavigate } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import {
  AlertCircle,
  Eye,
  EyeOff,
  Loader2,
  ShieldCheck,
  UserPlus,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { AuthLayout } from './auth-layout';
import { registerSchema, type RegisterFormValues } from './auth-schemas';
import { authService } from '@/services/auth-service';
import { normalizeApiError } from '@/services/api-error';
import { useAuthStore } from '@/stores/auth-store';
import { useUiStore } from '@/stores/ui-store';

export function RegisterPage() {
  const navigate = useNavigate();
  const isAuthenticated = useAuthStore((s) => s.isAuthenticated);
  const addToast = useUiStore((s) => s.addToast);

  const [showPassword, setShowPassword] = React.useState(false);
  const [showConfirmPassword, setShowConfirmPassword] = React.useState(false);
  const [submitError, setSubmitError] = React.useState<string | null>(null);
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterFormValues>({
    resolver: zodResolver(registerSchema),
    defaultValues: {
      full_name: '',
      email: '',
      password: '',
      confirm_password: '',
      accept_terms: false,
    },
  });

  if (isAuthenticated) {
    return <Navigate to="/app/dashboard" replace />;
  }

  const onSubmit = async (values: RegisterFormValues) => {
    setSubmitError(null);
    setIsSubmitting(true);
    try {
      const response = await authService.register({
        full_name: values.full_name.trim(),
        email: values.email.trim().toLowerCase(),
        password: values.password,
        confirm_password: values.confirm_password,
        accept_terms: values.accept_terms,
      });
      addToast({
        title: 'Governance Account Registered',
        description: `Welcome, ${response.user.full_name}. Assigned default role: ${response.user.role}.`,
        variant: 'success',
      });
      navigate('/app/dashboard', { replace: true });
    } catch (error) {
      const apiErr = normalizeApiError(error);
      setSubmitError(apiErr.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AuthLayout
      title="Register Operator Account"
      subtitle="Create a ParallaxAI account. New registrations receive the safe default VIEWER role until elevated by an administrator."
      footer={
        <span>
          Already have an operator account?{' '}
          <Link
            to="/login"
            className="font-semibold text-primary hover:underline"
          >
            Sign in to Command Center
          </Link>
        </span>
      }
    >
      <form
        onSubmit={handleSubmit(onSubmit)}
        noValidate
        className="space-y-4"
        aria-label="Operator registration form"
      >
        {submitError && (
          <div
            role="alert"
            data-testid="register-error-alert"
            className="flex items-start gap-2.5 rounded-md border border-red-500/40 bg-red-500/10 p-3 text-xs text-red-200"
          >
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-400" />
            <span>{submitError}</span>
          </div>
        )}

        {/* Default Role Security Notice */}
        <div
          data-testid="default-role-notice"
          className="flex items-start gap-2.5 rounded-md border border-primary/30 bg-primary/10 px-3 py-2.5 text-xs text-foreground"
        >
          <ShieldCheck className="mt-0.5 h-4 w-4 shrink-0 text-primary" />
          <div>
            <span className="font-semibold">Least-Privilege Provisioning: </span>
            <span className="text-muted-foreground">
              Self-registered accounts are automatically assigned the{' '}
              <code className="font-mono font-semibold text-primary">
                VIEWER
              </code>{' '}
              role. Privileged roles require administrator approval.
            </span>
          </div>
        </div>

        {/* Full Name */}
        <div className="space-y-1.5">
          <label
            htmlFor="register-full-name"
            className="block text-xs font-medium text-foreground"
          >
            Full Name
          </label>
          <Input
            id="register-full-name"
            type="text"
            autoComplete="name"
            placeholder="Dr. Elena Rostova"
            aria-invalid={Boolean(errors.full_name)}
            {...register('full_name')}
          />
          {errors.full_name && (
            <p role="alert" className="text-xs text-red-400">
              {errors.full_name.message}
            </p>
          )}
        </div>

        {/* Email */}
        <div className="space-y-1.5">
          <label
            htmlFor="register-email"
            className="block text-xs font-medium text-foreground"
          >
            Enterprise Email
          </label>
          <Input
            id="register-email"
            type="email"
            autoComplete="email"
            placeholder="elena.rostova@parallaxai.io"
            aria-invalid={Boolean(errors.email)}
            {...register('email')}
          />
          {errors.email && (
            <p role="alert" className="text-xs text-red-400">
              {errors.email.message}
            </p>
          )}
        </div>

        {/* Password */}
        <div className="space-y-1.5">
          <label
            htmlFor="register-password"
            className="block text-xs font-medium text-foreground"
          >
            Password
          </label>
          <div className="relative">
            <Input
              id="register-password"
              type={showPassword ? 'text' : 'password'}
              autoComplete="new-password"
              placeholder="Minimum 8 characters"
              aria-invalid={Boolean(errors.password)}
              className="pr-10"
              {...register('password')}
            />
            <button
              type="button"
              onClick={() => setShowPassword((prev) => !prev)}
              aria-label={showPassword ? 'Hide password' : 'Show password'}
              className="absolute right-2.5 top-2 rounded p-0.5 text-muted-foreground hover:text-foreground"
            >
              {showPassword ? (
                <EyeOff className="h-4 w-4" />
              ) : (
                <Eye className="h-4 w-4" />
              )}
            </button>
          </div>
          {errors.password && (
            <p role="alert" className="text-xs text-red-400">
              {errors.password.message}
            </p>
          )}
        </div>

        {/* Confirm Password */}
        <div className="space-y-1.5">
          <label
            htmlFor="register-confirm-password"
            className="block text-xs font-medium text-foreground"
          >
            Confirm Password
          </label>
          <div className="relative">
            <Input
              id="register-confirm-password"
              type={showConfirmPassword ? 'text' : 'password'}
              autoComplete="new-password"
              placeholder="Re-enter your password"
              aria-invalid={Boolean(errors.confirm_password)}
              className="pr-10"
              {...register('confirm_password')}
            />
            <button
              type="button"
              onClick={() => setShowConfirmPassword((prev) => !prev)}
              aria-label={
                showConfirmPassword
                  ? 'Hide confirm password'
                  : 'Show confirm password'
              }
              className="absolute right-2.5 top-2 rounded p-0.5 text-muted-foreground hover:text-foreground"
            >
              {showConfirmPassword ? (
                <EyeOff className="h-4 w-4" />
              ) : (
                <Eye className="h-4 w-4" />
              )}
            </button>
          </div>
          {errors.confirm_password && (
            <p role="alert" className="text-xs text-red-400">
              {errors.confirm_password.message}
            </p>
          )}
        </div>

        {/* Terms Acceptance */}
        <div className="space-y-1">
          <label
            htmlFor="register-accept-terms"
            className="flex cursor-pointer items-start gap-2.5 text-xs text-muted-foreground select-none"
          >
            <input
              id="register-accept-terms"
              type="checkbox"
              className="mt-0.5 h-3.5 w-3.5 rounded border-border bg-background text-primary focus:ring-primary"
              {...register('accept_terms')}
            />
            <span>
              I accept the ParallaxAI Governance Charter, audit trail logging
              policies, and role-based access terms.
            </span>
          </label>
          {errors.accept_terms && (
            <p role="alert" className="text-xs text-red-400">
              {errors.accept_terms.message}
            </p>
          )}
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
              <span>Provisioning Account…</span>
            </>
          ) : (
            <>
              <UserPlus className="h-4 w-4" />
              <span>Create Operator Account</span>
            </>
          )}
        </Button>
      </form>
    </AuthLayout>
  );
}

