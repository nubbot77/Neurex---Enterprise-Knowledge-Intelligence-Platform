import { ChevronRight } from 'lucide-react';
import { Link, useLocation } from 'react-router-dom';

export interface BreadcrumbItem {
  label: string;
  to?: string;
}

export interface BreadcrumbsProps {
  items?: BreadcrumbItem[];
}

function titleCase(segment: string): string {
  return segment.replace(/-/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());
}

/** Falls back to deriving crumbs from the URL when a page doesn't pass explicit `items`. */
function useDerivedItems(): BreadcrumbItem[] {
  const { pathname } = useLocation();
  const segments = pathname.split('/').filter(Boolean);

  return segments.map((segment, index) => ({
    label: titleCase(segment),
    to:
      index < segments.length - 1
        ? `/${segments.slice(0, index + 1).join('/')}`
        : undefined,
  }));
}

export function Breadcrumbs({ items }: BreadcrumbsProps) {
  const derived = useDerivedItems();
  const crumbs = items ?? derived;

  if (crumbs.length === 0) return null;

  return (
    <nav
      aria-label="Breadcrumb"
      className="flex items-center text-sm text-fg-muted"
    >
      {crumbs.map((crumb, index) => (
        <span key={`${crumb.label}-${index}`} className="flex items-center">
          {index > 0 && (
            <ChevronRight
              className="mx-1.5 size-3.5 shrink-0"
              aria-hidden="true"
            />
          )}
          {crumb.to ? (
            <Link to={crumb.to} className="transition-colors hover:text-fg">
              {crumb.label}
            </Link>
          ) : (
            <span aria-current="page" className="font-medium text-fg">
              {crumb.label}
            </span>
          )}
        </span>
      ))}
    </nav>
  );
}
