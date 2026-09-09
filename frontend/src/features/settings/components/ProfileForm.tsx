import { zodResolver } from '@hookform/resolvers/zod';
import { useState } from 'react';
import { useForm } from 'react-hook-form';
import { FormField, Input } from '@/components/ui';
import { useUpdateSettingsSection } from '../hooks';
import {
  profileSettingsSchema,
  type ProfileSettingsFormValues,
} from '../schemas';
import type { ProfileSettings } from '../types';
import { SettingsSectionCard } from './SettingsSectionCard';

export function ProfileForm({ profile }: { profile: ProfileSettings }) {
  const [saved, setSaved] = useState(false);
  const update = useUpdateSettingsSection('profile');

  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<ProfileSettingsFormValues>({
    resolver: zodResolver(profileSettingsSchema),
    defaultValues: profile,
  });

  const onSubmit = handleSubmit((values) => {
    update.mutate(values, { onSuccess: () => setSaved(true) });
  });

  return (
    <SettingsSectionCard
      title="Profile"
      description="Your personal account information."
      onSubmit={() => void onSubmit()}
      isPending={update.isPending}
      saved={saved}
    >
      <FormField label="Name" error={errors.name?.message}>
        {(field) => <Input {...field} {...register('name')} />}
      </FormField>
      <FormField label="Email" error={errors.email?.message}>
        {(field) => <Input type="email" {...field} {...register('email')} />}
      </FormField>
    </SettingsSectionCard>
  );
}
