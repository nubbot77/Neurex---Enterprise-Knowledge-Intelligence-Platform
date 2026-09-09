import { useState } from 'react';
import { Checkbox, FormField, Input } from '@/components/ui';
import { useUpdateSettingsSection } from '../hooks';
import type { SettingsBundle, SettingsSection } from '../types';
import { SettingsSectionCard } from './SettingsSectionCard';

export interface FieldConfig<T> {
  key: keyof T & string;
  label: string;
  type: 'text' | 'number' | 'checkbox';
}

export interface GenericSettingsFormProps<K extends SettingsSection> {
  section: K;
  title: string;
  description: string;
  fields: FieldConfig<SettingsBundle[K]>[];
  initialValues: SettingsBundle[K];
}

export function GenericSettingsForm<K extends SettingsSection>({
  section,
  title,
  description,
  fields,
  initialValues,
}: GenericSettingsFormProps<K>) {
  const [values, setValues] = useState(initialValues);
  const [saved, setSaved] = useState(false);
  const update = useUpdateSettingsSection(section);

  const setField = (key: keyof SettingsBundle[K], value: unknown) => {
    setValues((prev) => ({ ...prev, [key]: value }));
  };

  return (
    <SettingsSectionCard
      title={title}
      description={description}
      onSubmit={() =>
        update.mutate(values, { onSuccess: () => setSaved(true) })
      }
      isPending={update.isPending}
      saved={saved}
    >
      {fields.map((field) => {
        const value = values[field.key];
        if (field.type === 'checkbox') {
          return (
            <Checkbox
              key={field.key}
              label={field.label}
              checked={Boolean(value)}
              onChange={(e) => setField(field.key, e.target.checked)}
            />
          );
        }
        return (
          <FormField key={field.key} label={field.label}>
            {(fieldProps) => (
              <Input
                {...fieldProps}
                type={field.type}
                value={value as string | number}
                onChange={(e) =>
                  setField(
                    field.key,
                    field.type === 'number'
                      ? Number(e.target.value)
                      : e.target.value,
                  )
                }
              />
            )}
          </FormField>
        );
      })}
    </SettingsSectionCard>
  );
}
