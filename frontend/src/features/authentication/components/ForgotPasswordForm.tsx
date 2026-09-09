import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { Button, FormField, Input } from '@/components/ui';
import { toUserMessage } from '@/services/api/errors';
import { useForgotPassword } from '../hooks';
import {
  forgotPasswordSchema,
  type ForgotPasswordFormValues,
} from '../schemas';

export function ForgotPasswordForm() {
  const forgotPassword = useForgotPassword();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ForgotPasswordFormValues>({
    resolver: zodResolver(forgotPasswordSchema),
  });

  const onSubmit = handleSubmit((values) => forgotPassword.mutate(values));

  if (forgotPassword.isSuccess) {
    return (
      <p className="text-sm text-fg-muted">
        If an account exists for that email, a reset link is on its way.
      </p>
    );
  }

  return (
    <form
      onSubmit={(event) => {
        void onSubmit(event);
      }}
      noValidate
      className="space-y-4"
    >
      <FormField label="Email" error={errors.email?.message}>
        {(field) => (
          <Input
            type="email"
            autoComplete="email"
            {...field}
            {...register('email')}
          />
        )}
      </FormField>

      {forgotPassword.isError && (
        <p role="alert" className="text-sm text-danger">
          {toUserMessage(forgotPassword.error)}
        </p>
      )}

      <Button
        type="submit"
        className="w-full"
        loading={forgotPassword.isPending}
      >
        Send reset link
      </Button>
    </form>
  );
}
