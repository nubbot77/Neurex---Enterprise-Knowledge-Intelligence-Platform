import { zodResolver } from '@hookform/resolvers/zod';
import { useForm } from 'react-hook-form';
import { useLocation, useNavigate, type Location } from 'react-router-dom';
import { Button, FormField, Input } from '@/components/ui';
import { toUserMessage } from '@/services/api/errors';
import { useLogin } from '../hooks';
import { loginSchema, type LoginFormValues } from '../schemas';

interface LocationState {
  from?: Location;
}

export function LoginForm() {
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as LocationState | null)?.from;
  const login = useLogin();

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginFormValues>({ resolver: zodResolver(loginSchema) });

  const onSubmit = handleSubmit(async (values) => {
    await login.mutateAsync(values);
    await navigate(from?.pathname ?? '/dashboard', { replace: true });
  });

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

      <FormField label="Password" error={errors.password?.message}>
        {(field) => (
          <Input
            type="password"
            autoComplete="current-password"
            {...field}
            {...register('password')}
          />
        )}
      </FormField>

      {login.isError && (
        <p role="alert" className="text-sm text-danger">
          {toUserMessage(login.error)}
        </p>
      )}

      <Button type="submit" className="w-full" loading={login.isPending}>
        Log in
      </Button>
    </form>
  );
}
