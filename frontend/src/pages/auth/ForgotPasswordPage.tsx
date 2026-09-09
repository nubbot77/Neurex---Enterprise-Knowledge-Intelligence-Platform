import { Link } from 'react-router-dom';
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui';
import { ForgotPasswordForm } from '@/features/authentication/components';

export function ForgotPasswordPage() {
  return (
    <Card>
      <CardHeader>
        <CardTitle>Reset password</CardTitle>
        <CardDescription>
          We'll email you a link to reset your password.
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <ForgotPasswordForm />
        <p className="text-center text-sm text-fg-muted">
          Remembered it?{' '}
          <Link to="/login" className="text-accent hover:underline">
            Back to log in
          </Link>
        </p>
      </CardContent>
    </Card>
  );
}
