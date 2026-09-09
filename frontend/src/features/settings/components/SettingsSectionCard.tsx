import type { FormEvent, ReactNode } from 'react';
import {
  Button,
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from '@/components/ui';

export interface SettingsSectionCardProps {
  title: string;
  description: string;
  children: ReactNode;
  onSubmit: () => void;
  isPending: boolean;
  saved: boolean;
}

export function SettingsSectionCard({
  title,
  description,
  children,
  onSubmit,
  isPending,
  saved,
}: SettingsSectionCardProps) {
  const handleSubmit = (event: FormEvent) => {
    event.preventDefault();
    onSubmit();
  };

  return (
    <Card>
      <form onSubmit={handleSubmit}>
        <CardHeader>
          <CardTitle>{title}</CardTitle>
          <CardDescription>{description}</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">{children}</CardContent>
        <div className="flex items-center gap-3 border-t border-border p-4">
          <Button type="submit" loading={isPending} size="sm">
            Save changes
          </Button>
          {saved && <span className="text-xs text-success">Saved</span>}
        </div>
      </form>
    </Card>
  );
}
