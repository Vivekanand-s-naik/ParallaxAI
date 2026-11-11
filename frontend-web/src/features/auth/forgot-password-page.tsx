import * as React from 'react';
import { Link, useSearchParams } from 'react-router-dom';
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { useQuery } from '@tanstack/react-query';
import {
  AlertCircle,
  ArrowLeft,
  CheckCircle2,
  KeyRound,
  Loader2,
  MailWarning,
  Send,
} from 'lucide-react';
import { queryKeys } from '@/app/query-client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { AuthLayout } from './auth-layout';
import {
  forgotPasswordSchema,
  resetPasswordSchema,
  type ForgotPasswordFormValues,
  type ResetPasswordFormValues,
} from './auth-schemas';
import { authService } from '@/services/auth-service';
import { normalizeApiError } from '@/services/api-error';
import type { ForgotPasswordResponse } from '@/types/auth';

export function ForgotPasswordPage() {
  const [searchParams] = useSearchParams();
  const initialToken = searchParams.get('token') || '';

  const [mode, setMode] = React.useState<'request' | 'reset'>(
    initialToken ? 'reset' : 'request'
  );
  const [submitError, setSubmitError] = React.useState<string | null>(null);
  const [requestResult, setRequestResult] =
    React.useState<ForgotPasswordResponse | null>(null);
  const [resetSuccessMessage, setResetSuccessMessage] = React.useState<
    string | null
  >(null);
  const [isSubmitting, setIsSubmitting] = React.useState(false);

  const { data: providersStatus } = useQuery({
    queryKey: queryKeys.auth.providers(),
    queryFn: () => authService.getProvidersStatus(),
    staleTime: 60_000,
  });

  const requestForm = useForm<ForgotPasswordFormValues>({
    resolver: zodResolver(forgotPasswordSchema),
    defaultValues: { email: '' },
  });

  const resetForm = useForm<ResetPasswordFormValues>({
    resolver: zodResolver(resetPasswordSchema),
    defaultValues: {
      token: initialToken,
      new_password: '',
      confirm_password: '',
    },
  });

  const onRequestSubmit = async (values: ForgotPasswordFormValues) => {
    setSubmitError(null);
    setRequestResult(null);
    setIsSubmitting(true);
    try {
      const response = await authService.forgotPassword({
        email: values.email.trim().toLowerCase(),
      });
      setRequestResult(response);
    } catch (error) {
      const apiErr = normalizeApiError(error);
      setSubmitError(apiErr.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const onResetSubmit = async (values: ResetPasswordFormValues) => {
    setSubmitError(null);
    setResetSuccessMessage(null);
    setIsSubmitting(true);
    try {
      const response = await authService.resetPassword({
        token: values.token.trim(),
        new_password: values.new_password,
        confirm_password: values.confirm_password,
      });
      setResetSuccessMessage(response.message);
      resetForm.reset();
    } catch (error) {
      const apiErr = normalizeApiError(error);
      setSubmitError(apiErr.message);
    } finally {
      setIsSubmitting(false);
    }
  };

  const emailProviderConfigured = Boolean(
    providersStatus?.password_reset_email_enabled
  );

  return (
    <AuthLayout
      title={
        mode === 'request'
          ? 'Credential Recovery'
          : 'Complete Password Reset'
      }
      subtitle={
        mode === 'request'
          ? 'Request a password reset token for your ParallaxAI operator account.'
          : 'Enter your issued password reset token and choose a new password.'
      }
      footer={
        <Link
          to="/login"
          className="inline-flex items-center gap-1.5 font-semibold text-primary hover:underline"
        >
          <ArrowLeft className="h-3.5 w-3.5" />
          <span>Return to Operator Sign In</span>
        </Link>
      }
    >
      <div className="space-y-4">
        {/* Mode Switch Tabs */}
        <div className="grid grid-cols-2 gap-1 rounded-lg border border-border bg-background/70 p-1 text-xs">
          <button
            type="button"
            onClick={() => {
              setMode('request');
              setSubmitError(null);
            }}
            className={`rounded-md py-1.5 font-medium transition-colors ${
              mode === 'request'
                ? 'bg-primary/15 text-primary'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            1. Request Reset
          </button>
          <button
            type="button"
            onClick={() => {
              setMode('reset');
              setSubmitError(null);
            }}
            className={`rounded-md py-1.5 font-medium transition-colors ${
              mode === 'reset'
                ? 'bg-primary/15 text-primary'
                : 'text-muted-foreground hover:text-foreground'
            }`}
          >
            2. Enter Reset Token
          </button>
        </div>

        {/* Honest SMTP Provider Configuration Notice */}
        {!emailProviderConfigured && mode === 'request' && (
          <div
            data-testid="smtp-unavailable-banner"
            className="flex items-start gap-2.5 rounded-md border border-amber-500/40 bg-amber-500/10 p-3 text-xs text-amber-200"
          >
            <MailWarning className="mt-0.5 h-4 w-4 shrink-0 text-amber-400" />
            <div>
              <p className="font-semibold text-amber-300">
                Outbound Email Delivery (SMTP) Not Configured
              </p>
              <p className="mt-0.5 text-amber-200/90">
                {providersStatus?.password_reset_message ||
                  'Password reset tokens are generated and stored in PostgreSQL, but no outbound email is sent until an SMTP provider is configured.'}
              </p>
            </div>
          </div>
        )}

        {submitError && (
          <div
            role="alert"
            data-testid="forgot-password-error"
            className="flex items-start gap-2.5 rounded-md border border-red-500/40 bg-red-500/10 p-3 text-xs text-red-200"
          >
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0 text-red-400" />
            <span>{submitError}</span>
          </div>
        )}

        {mode === 'request' ? (
          <form
            onSubmit={requestForm.handleSubmit(onRequestSubmit)}
            noValidate
            className="space-y-4"
            aria-label="Password reset request form"
          >
            {requestResult && (
              <div
                role="status"
                data-testid="forgot-password-response"
                className={`flex items-start gap-2.5 rounded-md border p-3 text-xs ${
                  requestResult.email_provider_configured
                    ? 'border-emerald-500/40 bg-emerald-500/10 text-emerald-200'
                    : 'border-amber-500/40 bg-amber-500/10 text-amber-200'
                }`}
              >
                {requestResult.email_provider_configured ? (
                  <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" />
                ) : (
                  <MailWarning className="mt-0.5 h-4 w-4 shrink-0 text-amber-400" />
                )}
                <div>
                  <p className="font-semibold">
                    Status: {requestResult.status}
                  </p>
                  <p className="mt-0.5">{requestResult.message}</p>
                </div>
              </div>
            )}

            <div className="space-y-1.5">
              <label
                htmlFor="forgot-email"
                className="block text-xs font-medium text-foreground"
              >
                Account Email Address
              </label>
              <Input
                id="forgot-email"
                type="email"
                autoComplete="email"
                placeholder="operator@parallaxai.io"
                aria-invalid={Boolean(requestForm.formState.errors.email)}
                {...requestForm.register('email')}
              />
              {requestForm.formState.errors.email && (
                <p role="alert" className="text-xs text-red-400">
                  {requestForm.formState.errors.email.message}
                </p>
              )}
            </div>

            <Button
              type="submit"
              disabled={isSubmitting}
              className="w-full"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Processing Request…</span>
                </>
              ) : (
                <>
                  <Send className="h-4 w-4" />
                  <span>Request Password Reset</span>
                </>
              )}
            </Button>
          </form>
        ) : (
          <form
            onSubmit={resetForm.handleSubmit(onResetSubmit)}
            noValidate
            className="space-y-4"
            aria-label="Password reset token completion form"
          >
            {resetSuccessMessage && (
              <div
                role="status"
                data-testid="reset-password-success"
                className="flex items-start gap-2.5 rounded-md border border-emerald-500/40 bg-emerald-500/10 p-3 text-xs text-emerald-200"
              >
                <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-emerald-400" />
                <div>
                  <p className="font-semibold">Password Updated</p>
                  <p className="mt-0.5">{resetSuccessMessage}</p>
                  <Link
                    to="/login"
                    className="mt-2 inline-block font-semibold text-primary underline"
                  >
                    Proceed to Sign In →
                  </Link>
                </div>
              </div>
            )}

            <div className="space-y-1.5">
              <label
                htmlFor="reset-token"
                className="block text-xs font-medium text-foreground"
              >
                Reset Token
              </label>
              <Input
                id="reset-token"
                type="text"
                placeholder="Paste your issued reset token"
                className="font-mono text-xs"
                aria-invalid={Boolean(resetForm.formState.errors.token)}
                {...resetForm.register('token')}
              />
              {resetForm.formState.errors.token && (
                <p role="alert" className="text-xs text-red-400">
                  {resetForm.formState.errors.token.message}
                </p>
              )}
            </div>

            <div className="space-y-1.5">
              <label
                htmlFor="reset-new-password"
                className="block text-xs font-medium text-foreground"
              >
                New Password
              </label>
              <Input
                id="reset-new-password"
                type="password"
                autoComplete="new-password"
                placeholder="Minimum 8 characters"
                aria-invalid={Boolean(resetForm.formState.errors.new_password)}
                {...resetForm.register('new_password')}
              />
              {resetForm.formState.errors.new_password && (
                <p role="alert" className="text-xs text-red-400">
                  {resetForm.formState.errors.new_password.message}
                </p>
              )}
            </div>

            <div className="space-y-1.5">
              <label
                htmlFor="reset-confirm-password"
                className="block text-xs font-medium text-foreground"
              >
                Confirm New Password
              </label>
              <Input
                id="reset-confirm-password"
                type="password"
                autoComplete="new-password"
                placeholder="Re-enter your new password"
                aria-invalid={Boolean(
                  resetForm.formState.errors.confirm_password
                )}
                {...resetForm.register('confirm_password')}
              />
              {resetForm.formState.errors.confirm_password && (
                <p role="alert" className="text-xs text-red-400">
                  {resetForm.formState.errors.confirm_password.message}
                </p>
              )}
            </div>

            <Button
              type="submit"
              disabled={isSubmitting}
              className="w-full"
            >
              {isSubmitting ? (
                <>
                  <Loader2 className="h-4 w-4 animate-spin" />
                  <span>Resetting Password…</span>
                </>
              ) : (
                <>
                  <KeyRound className="h-4 w-4" />
                  <span>Update Password</span>
                </>
              )}
            </Button>
          </form>
        )}
      </div>
    </AuthLayout>
  );
}

