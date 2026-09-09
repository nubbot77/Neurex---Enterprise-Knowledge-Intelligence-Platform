import { isRouteErrorResponse, Link, useRouteError } from 'react-router-dom';
import { buttonVariants } from '@/components/ui';

/** Root errorElement — catches render/loader/lazy-import failures anywhere in the route tree. */
export function RouteErrorPage() {
  const error = useRouteError();

  const status = isRouteErrorResponse(error) ? error.status : undefined;
  const message = isRouteErrorResponse(error)
    ? error.statusText
    : error instanceof Error
      ? error.message
      : 'An unexpected error occurred.';

  return (
    <div className="flex min-h-screen flex-col items-center justify-center gap-4 p-6 text-center">
      <p className="text-sm font-medium text-danger">{status ?? 'Error'}</p>
      <h1 className="text-2xl font-semibold text-fg">Something went wrong</h1>
      <p className="max-w-sm text-sm text-fg-muted">{message}</p>
      <Link to="/dashboard" className={buttonVariants({ variant: 'primary' })}>
        Back to dashboard
      </Link>
    </div>
  );
}
