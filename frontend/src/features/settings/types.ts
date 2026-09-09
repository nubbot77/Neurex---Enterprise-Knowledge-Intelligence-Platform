export interface ProfileSettings {
  name: string;
  email: string;
}

export interface OrganizationSettings {
  name: string;
  domain: string;
}

export interface ApiSettings {
  apiKeyMasked: string;
  webhookUrl: string;
}

export interface ModelSettings {
  provider: string;
  model: string;
  temperature: number;
}

export interface RetrievalSettings {
  topK: number;
  hybridAlpha: number;
  rerankerEnabled: boolean;
}

export interface NotificationSettings {
  emailOnIngestionFailure: boolean;
  emailOnEvaluationComplete: boolean;
}

export interface SecuritySettings {
  twoFactorEnabled: boolean;
  sessionTimeoutMinutes: number;
}

export interface SettingsBundle {
  profile: ProfileSettings;
  organization: OrganizationSettings;
  api: ApiSettings;
  model: ModelSettings;
  retrieval: RetrievalSettings;
  notifications: NotificationSettings;
  security: SecuritySettings;
}

export type SettingsSection = keyof SettingsBundle;
