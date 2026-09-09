import {
  ErrorState,
  Skeleton,
  Tabs,
  TabsList,
  TabsPanel,
  TabsTrigger,
} from '@/components/ui';
import {
  AppearanceForm,
  GenericSettingsForm,
  ProfileForm,
} from '@/features/settings/components';
import { useSettings } from '@/features/settings/hooks';
import { toUserMessage } from '@/services/api/errors';

export function SettingsPage() {
  const { data, isLoading, isError, error, refetch } = useSettings();

  return (
    <div className="mx-auto max-w-2xl space-y-4 p-6">
      <div>
        <h1 className="text-xl font-semibold text-fg">Settings</h1>
        <p className="text-sm text-fg-muted">
          Profile, organization, API, model, retrieval, and appearance settings.
        </p>
      </div>

      {isLoading && (
        <div className="space-y-3">
          <Skeleton className="h-40 w-full" />
          <Skeleton className="h-40 w-full" />
        </div>
      )}

      {isError && (
        <ErrorState
          description={toUserMessage(error)}
          onRetry={() => void refetch()}
        />
      )}

      {!isLoading && !isError && data && (
        <Tabs defaultValue="profile">
          <TabsList className="flex-wrap">
            <TabsTrigger value="profile">Profile</TabsTrigger>
            <TabsTrigger value="appearance">Appearance</TabsTrigger>
            <TabsTrigger value="organization">Organization</TabsTrigger>
            <TabsTrigger value="api">API</TabsTrigger>
            <TabsTrigger value="model">Model</TabsTrigger>
            <TabsTrigger value="retrieval">Retrieval</TabsTrigger>
            <TabsTrigger value="notifications">Notifications</TabsTrigger>
            <TabsTrigger value="security">Security</TabsTrigger>
          </TabsList>

          <TabsPanel value="profile">
            <ProfileForm profile={data.profile} />
          </TabsPanel>

          <TabsPanel value="appearance">
            <AppearanceForm />
          </TabsPanel>

          <TabsPanel value="organization">
            <GenericSettingsForm
              section="organization"
              title="Organization"
              description="Workspace-level details."
              initialValues={data.organization}
              fields={[
                { key: 'name', label: 'Organization name', type: 'text' },
                { key: 'domain', label: 'Domain', type: 'text' },
              ]}
            />
          </TabsPanel>

          <TabsPanel value="api">
            <GenericSettingsForm
              section="api"
              title="API configuration"
              description="Credentials and webhooks for programmatic access."
              initialValues={data.api}
              fields={[
                { key: 'apiKeyMasked', label: 'API key', type: 'text' },
                { key: 'webhookUrl', label: 'Webhook URL', type: 'text' },
              ]}
            />
          </TabsPanel>

          <TabsPanel value="model">
            <GenericSettingsForm
              section="model"
              title="Model configuration"
              description="Which LLM provider and model answer chat queries."
              initialValues={data.model}
              fields={[
                { key: 'provider', label: 'Provider', type: 'text' },
                { key: 'model', label: 'Model', type: 'text' },
                { key: 'temperature', label: 'Temperature', type: 'number' },
              ]}
            />
          </TabsPanel>

          <TabsPanel value="retrieval">
            <GenericSettingsForm
              section="retrieval"
              title="Retrieval configuration"
              description="Tuning for hybrid search and reranking."
              initialValues={data.retrieval}
              fields={[
                { key: 'topK', label: 'Top K', type: 'number' },
                {
                  key: 'hybridAlpha',
                  label: 'Hybrid alpha (lexical vs dense)',
                  type: 'number',
                },
                {
                  key: 'rerankerEnabled',
                  label: 'Enable reranker',
                  type: 'checkbox',
                },
              ]}
            />
          </TabsPanel>

          <TabsPanel value="notifications">
            <GenericSettingsForm
              section="notifications"
              title="Notification preferences"
              description="Email alerts for background events."
              initialValues={data.notifications}
              fields={[
                {
                  key: 'emailOnIngestionFailure',
                  label: 'Email on ingestion failure',
                  type: 'checkbox',
                },
                {
                  key: 'emailOnEvaluationComplete',
                  label: 'Email when an evaluation run completes',
                  type: 'checkbox',
                },
              ]}
            />
          </TabsPanel>

          <TabsPanel value="security">
            <GenericSettingsForm
              section="security"
              title="Security"
              description="Account protection and session policy."
              initialValues={data.security}
              fields={[
                {
                  key: 'twoFactorEnabled',
                  label: 'Require two-factor authentication',
                  type: 'checkbox',
                },
                {
                  key: 'sessionTimeoutMinutes',
                  label: 'Session timeout (minutes)',
                  type: 'number',
                },
              ]}
            />
          </TabsPanel>
        </Tabs>
      )}
    </div>
  );
}
