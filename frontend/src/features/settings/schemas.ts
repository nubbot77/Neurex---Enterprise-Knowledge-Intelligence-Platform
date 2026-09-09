import { z } from 'zod';

export const profileSettingsSchema = z.object({
  name: z.string().min(2, 'Name must be at least 2 characters'),
  email: z.email('Enter a valid email address'),
});
export type ProfileSettingsFormValues = z.infer<typeof profileSettingsSchema>;
