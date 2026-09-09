import { createBrowserRouter, Navigate } from 'react-router-dom';
import { AppShell, AuthLayout } from '@/components/layout';
import {
  GuestRoute,
  ProtectedRoute,
} from '@/features/authentication/components';
import { RouteErrorPage } from '@/pages/errors/RouteErrorPage';

export const router = createBrowserRouter([
  {
    path: '/',
    element: (
      <ProtectedRoute>
        <AppShell />
      </ProtectedRoute>
    ),
    errorElement: <RouteErrorPage />,
    children: [
      { index: true, element: <Navigate to="/dashboard" replace /> },
      {
        path: 'dashboard',
        lazy: async () => {
          const { DashboardPage } =
            await import('@/pages/dashboard/DashboardPage');
          return { Component: DashboardPage };
        },
      },
      {
        path: 'documents',
        lazy: async () => {
          const { DocumentsPage } =
            await import('@/pages/documents/DocumentsPage');
          return { Component: DocumentsPage };
        },
      },
      {
        path: 'documents/:documentId',
        lazy: async () => {
          const { DocumentDetailPage } =
            await import('@/pages/documents/DocumentDetailPage');
          return { Component: DocumentDetailPage };
        },
      },
      {
        path: 'search',
        lazy: async () => {
          const { SearchPage } = await import('@/pages/search/SearchPage');
          return { Component: SearchPage };
        },
      },
      {
        path: 'chat',
        lazy: async () => {
          const { ChatPage } = await import('@/pages/chat/ChatPage');
          return { Component: ChatPage };
        },
      },
      {
        path: 'chat/:conversationId',
        lazy: async () => {
          const { ChatPage } = await import('@/pages/chat/ChatPage');
          return { Component: ChatPage };
        },
      },
      {
        path: 'evaluations',
        lazy: async () => {
          const { EvaluationsPage } =
            await import('@/pages/evaluations/EvaluationsPage');
          return { Component: EvaluationsPage };
        },
      },
      {
        path: 'evaluations/datasets',
        lazy: async () => {
          const { EvaluationDatasetsPage } =
            await import('@/pages/evaluations/EvaluationDatasetsPage');
          return { Component: EvaluationDatasetsPage };
        },
      },
      {
        path: 'evaluations/runs',
        lazy: async () => {
          const { EvaluationRunsPage } =
            await import('@/pages/evaluations/EvaluationRunsPage');
          return { Component: EvaluationRunsPage };
        },
      },
      {
        path: 'settings',
        lazy: async () => {
          const { SettingsPage } =
            await import('@/pages/settings/SettingsPage');
          return { Component: SettingsPage };
        },
      },
    ],
  },
  {
    element: (
      <GuestRoute>
        <AuthLayout />
      </GuestRoute>
    ),
    errorElement: <RouteErrorPage />,
    children: [
      {
        path: 'login',
        lazy: async () => {
          const { LoginPage } = await import('@/pages/auth/LoginPage');
          return { Component: LoginPage };
        },
      },
      {
        path: 'register',
        lazy: async () => {
          const { RegisterPage } = await import('@/pages/auth/RegisterPage');
          return { Component: RegisterPage };
        },
      },
      {
        path: 'forgot-password',
        lazy: async () => {
          const { ForgotPasswordPage } =
            await import('@/pages/auth/ForgotPasswordPage');
          return { Component: ForgotPasswordPage };
        },
      },
      {
        path: 'reset-password',
        lazy: async () => {
          const { ResetPasswordPage } =
            await import('@/pages/auth/ResetPasswordPage');
          return { Component: ResetPasswordPage };
        },
      },
    ],
  },
  {
    path: '*',
    lazy: async () => {
      const { NotFoundPage } = await import('@/pages/errors/NotFoundPage');
      return { Component: NotFoundPage };
    },
  },
]);
