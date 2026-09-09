import { EmptyState } from '@/components/ui';

export interface PageStubProps {
  title: string;
  description: string;
}

/** Placeholder for routes whose real implementation lands in a later phase. */
export function PageStub({ title, description }: PageStubProps) {
  return (
    <div className="p-6">
      <h1 className="text-xl font-semibold text-fg">{title}</h1>
      <p className="mt-1 text-sm text-fg-muted">{description}</p>
      <EmptyState
        className="mt-8"
        title="Not built yet"
        description="This screen is scheduled for a later phase."
      />
    </div>
  );
}
