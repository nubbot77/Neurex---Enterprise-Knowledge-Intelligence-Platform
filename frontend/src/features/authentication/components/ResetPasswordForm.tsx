import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { Button, ErrorState, FormField, Input } from '@/components/ui';
import { toUserMessage } from '@/services/api/errors';
import { useResetPassword } from '../hooks';
import { resetPasswordSchema, type ResetPasswordFormValues } from '../schemas';

export function ResetPasswordForm() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const token = searchParams.get('token');
  const resetPassword = useResetPassword();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ResetPasswordFormValues>({
    resolver: zodResolver(resetPasswordSchema),
  });

  if (!token) {
    return (
      <ErrorState
        title="Invalid or expired link"
        description="Request a new password reset link and try again."
      />
    );
  }

  const onSubmit = handleSubmit(async (values) => {
    await resetPassword.mutateAsync({ token, password: values.password });
    await navigate('/login', { replace: true });
  });

  return (
    <form
      onSubmit={(event) => {
        void onSubmit(event);
      }}
      noValidate
      className="space-y-4"
    >
      <FormField label="New password" error={errors.password?.message}>
        {(field) => (
          <Input
            type="password"
            autoComplete="new-password"
            {...field}
            {...register('password')}
          />
        )}
      </FormField>

      <FormField
        label="Confirm new password"
        error={errors.confirmPassword?.message}
      >
        {(field) => (
          <Input
            type="password"
            autoComplete="new-password"
            {...field}
            {...register('confirmPassword')}
          />
        )}
      </FormField>

      {resetPassword.isError && (
        <p role="alert" className="text-sm text-danger">
          {toUserMessage(resetPassword.error)}
        </p>
      )}

      <Button
        type="submit"
        className="w-full"
        loading={resetPassword.isPending}
      >
        Reset password
      </Button>
    </form>
  );
}
