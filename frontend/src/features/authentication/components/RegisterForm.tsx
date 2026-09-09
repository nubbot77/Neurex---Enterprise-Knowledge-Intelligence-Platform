import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { useNavigate } from 'react-router-dom';
import { Button, FormField, Input } from '@/components/ui';
import { toUserMessage } from '@/services/api/errors';
import { useRegister } from '../hooks';
import { registerSchema, type RegisterFormValues } from '../schemas';

export function RegisterForm() {
  const navigate = useNavigate();
  const registerMutation = useRegister();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<RegisterFormValues>({ resolver: zodResolver(registerSchema) });

  const onSubmit = handleSubmit(async (values) => {
    await registerMutation.mutateAsync(values);
    await navigate('/dashboard', { replace: true });
  });

  return (
    <form
      onSubmit={(event) => {
        void onSubmit(event);
      }}
      noValidate
      className="space-y-4"
    >
      <FormField label="Name" error={errors.name?.message}>
        {(field) => (
          <Input autoComplete="name" {...field} {...register('name')} />
        )}
      </FormField>

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

      <FormField label="Password" error={errors.password?.message}>
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
        label="Confirm password"
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

      {registerMutation.isError && (
        <p role="alert" className="text-sm text-danger">
          {toUserMessage(registerMutation.error)}
        </p>
      )}

      <Button
        type="submit"
        className="w-full"
        loading={registerMutation.isPending}
      >
        Create account
      </Button>
    </form>
  );
}
