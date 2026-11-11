import { fireEvent, render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, useRoutes } from 'react-router-dom';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { AppProviders } from '@/app/providers';
import { createAppQueryClient } from '@/app/query-client';
import { appRoutes } from '@/app/router';
import { ApiError } from '@/services/api-error';
import { authService } from '@/services/auth-service';
import { useAuthStore } from '@/stores/auth-store';
import { useUiStore } from '@/stores/ui-store';
import type { UserAuth } from '@/types/auth';

const MOCK_VIEWER_USER: UserAuth = {
  id: '00000000-0000-0000-0000-000000000010',
  username: 'elena.rostova',
  email: 'elena.rostova@parallaxai.io',
  full_name: 'Dr. Elena Rostova',
  role: 'VIEWER',
  roles: ['VIEWER'],
  permissions: [
    'decisions:read',
    'agents:read',
    'voting:read',
    'governance:read',
    'bias:read',
    'notifications:read',
  ],
  is_active: true,
  is_verified: true,
  auth_provider: 'local',
  preferences: {},
};

function renderAuthRouter(initialEntries: string[]) {
  const client = createAppQueryClient();
  return render(
    <AppProviders client={client}>
      <MemoryRouter initialEntries={initialEntries}>
        <RoutesRenderer />
      </MemoryRouter>
    </AppProviders>
  );
}

function RoutesRenderer() {
  return useRoutes(appRoutes);
}

describe('Phase 7 — Authentication Screens (Login, Register, Forgot Password)', () => {
  beforeEach(() => {
    vi.restoreAllMocks();
    useAuthStore.getState().clearSession();
    useAuthStore.getState().setInitialized(true);
    useUiStore.setState({ toasts: [] });

    vi.spyOn(authService, 'getProvidersStatus').mockResolvedValue({
      local_enabled: true,
      google_oauth_enabled: false,
      google_oauth_message:
        'Google Sign-In is currently unavailable: GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, and GOOGLE_REDIRECT_URI are not configured.',
      password_reset_email_enabled: false,
      password_reset_message:
        'Outbound email provider (SMTP) is not configured. Password reset tokens are generated in the database.',
    });
  });

  it('validates login fields, toggles password visibility, shows honest disabled Google OAuth state, and logs in', async () => {
    const loginSpy = vi
      .spyOn(authService, 'login')
      .mockImplementation(async () => {
        useAuthStore
          .getState()
          .setSession(MOCK_VIEWER_USER, 'valid-jwt-access-token');
        return {
          token: 'valid-jwt-access-token',
          access_token: 'valid-jwt-access-token',
          token_type: 'bearer',
          expires_in: 900,
          user: MOCK_VIEWER_USER,
        };
      });

    renderAuthRouter(['/login']);

    // Submit empty form -> validation messages appear
    const submitBtn = screen.getByRole('button', {
      name: /sign in to command center/i,
    });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(
        screen.getByText('Email or username is required')
      ).toBeInTheDocument();
      expect(screen.getByText('Password is required')).toBeInTheDocument();
    });

    // Show / Hide password toggle
    const passwordInput = screen.getByLabelText('Password') as HTMLInputElement;
    expect(passwordInput.type).toBe('password');
    const toggleBtn = screen.getByRole('button', { name: 'Show password' });
    fireEvent.click(toggleBtn);
    expect(passwordInput.type).toBe('text');

    // Honest Google OAuth button is disabled when credentials are not configured
    await waitFor(() => {
      const googleBtn = screen.getByTestId('google-oauth-button');
      expect(googleBtn).toBeDisabled();
      expect(
        screen.getByTestId('google-oauth-unavailable-notice')
      ).toHaveTextContent(/GOOGLE_CLIENT_ID/i);
    });

    // Fill valid credentials and submit
    fireEvent.change(screen.getByLabelText('Email or Username'), {
      target: { value: 'elena.rostova@parallaxai.io' },
    });
    fireEvent.change(passwordInput, {
      target: { value: 'StrongPassword!123' },
    });
    fireEvent.click(submitBtn);

    await waitFor(() => {
      expect(loginSpy).toHaveBeenCalledWith({
        identifier: 'elena.rostova@parallaxai.io',
        password: 'StrongPassword!123',
        remember_me: false,
      });
      // Redirected to /app/dashboard
      expect(
        screen.getByRole('heading', { name: 'Command Center' })
      ).toBeInTheDocument();
    });
  });

  it('displays server error alert when login fails with 401', async () => {
    vi.spyOn(authService, 'login').mockRejectedValue(
      new ApiError({
        message: 'Invalid email/username or password',
        status: 401,
        code: 'http_401',
      })
    );

    renderAuthRouter(['/login']);

    fireEvent.change(screen.getByLabelText('Email or Username'), {
      target: { value: 'admin@parallaxai.io' },
    });
    fireEvent.change(screen.getByLabelText('Password'), {
      target: { value: 'wrong-pass' },
    });
    fireEvent.click(
      screen.getByRole('button', { name: /sign in to command center/i })
    );

    await waitFor(() => {
      expect(screen.getByTestId('login-error-alert')).toHaveTextContent(
        'Invalid email/username or password'
      );
    });
  });

  it('validates registration password match & terms acceptance and provisions VIEWER account', async () => {
    const registerSpy = vi
      .spyOn(authService, 'register')
      .mockImplementation(async () => {
        useAuthStore
          .getState()
          .setSession(MOCK_VIEWER_USER, 'new-viewer-token');
        return {
          token: 'new-viewer-token',
          access_token: 'new-viewer-token',
          token_type: 'bearer',
          expires_in: 900,
          user: MOCK_VIEWER_USER,
        };
      });

    renderAuthRouter(['/register']);

    // Verify Least-Privilege VIEWER notice is visible and no role selector exists
    expect(screen.getByTestId('default-role-notice')).toHaveTextContent(
      'VIEWER'
    );

    fireEvent.change(screen.getByLabelText('Full Name'), {
      target: { value: 'Dr. Elena Rostova' },
    });
    fireEvent.change(screen.getByLabelText('Enterprise Email'), {
      target: { value: 'elena.rostova@parallaxai.io' },
    });
    fireEvent.change(screen.getByLabelText('Password'), {
      target: { value: 'PasswordOne123!' },
    });
    fireEvent.change(screen.getByLabelText('Confirm Password'), {
      target: { value: 'DifferentPassword999!' },
    });

    fireEvent.click(
      screen.getByRole('button', { name: /create operator account/i })
    );

    await waitFor(() => {
      expect(screen.getByText('Passwords do not match')).toBeInTheDocument();
      expect(
        screen.getByText(
          'You must accept the governance platform terms to register'
        )
      ).toBeInTheDocument();
    });

    // Fix confirm password and check terms
    fireEvent.change(screen.getByLabelText('Confirm Password'), {
      target: { value: 'PasswordOne123!' },
    });
    fireEvent.click(screen.getByRole('checkbox'));
    fireEvent.click(
      screen.getByRole('button', { name: /create operator account/i })
    );

    await waitFor(() => {
      expect(registerSpy).toHaveBeenCalledTimes(1);
      expect(
        screen.getByRole('heading', { name: 'Command Center' })
      ).toBeInTheDocument();
    });
  });

  it('honestly reports when SMTP email provider is not configured on Forgot Password screen', async () => {
    vi.spyOn(authService, 'forgotPassword').mockResolvedValue({
      status: 'email_provider_not_configured',
      email_provider_configured: false,
      message:
        'Password reset architecture is active, but an outbound email provider (SMTP) has not been configured in this environment. No email was sent.',
    });

    renderAuthRouter(['/forgot-password']);

    await waitFor(() => {
      expect(screen.getByTestId('smtp-unavailable-banner')).toHaveTextContent(
        /Outbound Email Delivery \(SMTP\) Not Configured/i
      );
    });

    fireEvent.change(screen.getByLabelText('Account Email Address'), {
      target: { value: 'elena.rostova@parallaxai.io' },
    });
    fireEvent.click(
      screen.getByRole('button', { name: /request password reset/i })
    );

    await waitFor(() => {
      const responseBox = screen.getByTestId('forgot-password-response');
      expect(responseBox).toHaveTextContent('email_provider_not_configured');
      expect(responseBox).toHaveTextContent('No email was sent.');
    });
  });
});

