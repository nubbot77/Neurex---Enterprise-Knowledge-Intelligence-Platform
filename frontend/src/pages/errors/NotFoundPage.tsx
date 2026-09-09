import { Link } from 'react-router-dom';
import { buttonVariants } from '@/components/ui';

export function NotFoundPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 p-6 text-center">
      <p className="text-sm font-medium text-accent">404</p>
      <h1 className="text-2xl font-semibold text-fg">Page not found</h1>
      <p className="max-w-sm text-sm text-fg-muted">
        The page you're looking for doesn't exist or may have been moved.
      </p>
      <Link to="/dashboard" className={buttonVariants({ variant: 'primary' })}>
        Back to dashboard
      </Link>
    </div>
  );
}
