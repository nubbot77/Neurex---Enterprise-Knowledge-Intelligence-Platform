import { Spinner } from '@/components/ui';

export function FullscreenLoader() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-surface">
      <Spinner size={24} label="Loading session" />
    </div>
  );
}
