import {
  BarChart3,
  FileText,
  LayoutDashboard,
  MessageSquare,
  Search,
  Settings,
  type LucideIcon,
} from 'lucide-react';

export interface NavItem {
  label: string;
  to: string;
  icon: LucideIcon;
}

export interface NavGroup {
  label?: string;
  items: NavItem[];
}

/** Single source of truth for sidebar/mobile-nav links, so both stay in sync. */
export const navGroups: NavGroup[] = [
  {
    items: [{ label: 'Dashboard', to: '/dashboard', icon: LayoutDashboard }],
  },
  {
    label: 'Knowledge',
    items: [
      { label: 'Documents', to: '/documents', icon: FileText },
      { label: 'Search', to: '/search', icon: Search },
    ],
  },
  {
    label: 'AI',
    items: [{ label: 'Chat', to: '/chat', icon: MessageSquare }],
  },
  {
    label: 'Evaluation',
    items: [{ label: 'Evaluations', to: '/evaluations', icon: BarChart3 }],
  },
  {
    label: 'System',
    items: [{ label: 'Settings', to: '/settings', icon: Settings }],
  },
];
