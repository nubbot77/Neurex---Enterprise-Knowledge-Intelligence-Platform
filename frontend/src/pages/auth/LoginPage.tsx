import { Link } from 'react-router-dom';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui';
import { LoginForm } from '@/features/authentication/components';

export function LoginPage() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Log in</CardTitle>
        <CardDescription>Sign in to your Neurex workspace.</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <LoginForm />
        <p className="text-center text-sm text-fg-muted">
          No account?{' '}
          <Link to="/register" className="text-accent hover:underline">
            Register
          </Link>{' '}
          ·{' '}
          <Link to="/forgot-password" className="text-accent hover:underline">
            Forgot password
          </Link>
        </p>
      </CardContent>
    </Card>
  );
}
