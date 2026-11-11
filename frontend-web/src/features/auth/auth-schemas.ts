import { z } from 'zod';

export const loginSchema = z.object({
  identifier: z
    .string()
    .trim()
    .min(1, 'Email or username is required'),
  password: z
    .string()
    .min(1, 'Password is required'),
  remember_me: z.boolean().default(false),
});

export type LoginFormValues = z.infer<typeof loginSchema>;

export const registerSchema = z
  .object({
    full_name: z
      .string()
      .trim()
      .min(2, 'Full name must be at least 2 characters')
      .max(255, 'Full name is too long'),
    email: z
      .string()
      .trim()
      .min(1, 'Email address is required')
      .email('Enter a valid enterprise email address'),
    password: z
      .string()
      .min(8, 'Password must be at least 8 characters')
      .max(128, 'Password must not exceed 128 characters'),
    confirm_password: z
      .string()
      .min(1, 'Please confirm your password'),
    accept_terms: z
      .boolean()
      .refine((val) => val === true, {
        message: 'You must accept the governance platform terms to register',
      }),
  })
  .refine((data) => data.password === data.confirm_password, {
    path: ['confirm_password'],
    message: 'Passwords do not match',
  });

export type RegisterFormValues = z.infer<typeof registerSchema>;

export const forgotPasswordSchema = z.object({
  email: z
    .string()
    .trim()
    .min(1, 'Email address is required')
    .email('Enter a valid email address'),
});

export type ForgotPasswordFormValues = z.infer<typeof forgotPasswordSchema>;

export const resetPasswordSchema = z
  .object({
    token: z
      .string()
      .trim()
      .min(16, 'Reset token must be at least 16 characters'),
    new_password: z
      .string()
      .min(8, 'New password must be at least 8 characters')
      .max(128, 'New password must not exceed 128 characters'),
    confirm_password: z
      .string()
      .min(1, 'Please confirm your new password'),
  })
  .refine((data) => data.new_password === data.confirm_password, {
    path: ['confirm_password'],
    message: 'New passwords do not match',
  });

export type ResetPasswordFormValues = z.infer<typeof resetPasswordSchema>;

