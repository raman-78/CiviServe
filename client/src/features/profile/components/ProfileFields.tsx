/**
 * Reusable react-hook-form field components for the profile form. Shared by the
 * single-page edit form and the multi-step setup wizard so both validate the
 * same schema (`features/profile/profileSchema.ts`).
 */
import { useFormContext, type FieldPath } from "react-hook-form";
import { Checkbox } from "@/components/ui/checkbox";
import {
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { applyUILanguage } from "@/i18n";
import { SUPPORTED_UI_LANGUAGES } from "@/lib/constants";
import { useSettingsStore } from "@/store/settingsSlice";
import type { LanguageCode } from "@civiserve/shared";
import type { ProfileFormValues } from "@/features/profile/profileSchema";

type FieldName = FieldPath<ProfileFormValues>;

interface InputFieldProps {
  name: FieldName;
  label: string;
  placeholder?: string;
  type?: "text" | "email" | "tel" | "number";
}

export function ProfileInputField({ name, label, placeholder, type = "text" }: InputFieldProps) {
  const { control } = useFormContext<ProfileFormValues>();
  return (
    <FormField
      control={control}
      name={name}
      render={({ field }) => (
        <FormItem>
          <FormLabel>{label}</FormLabel>
          <FormControl>
            <Input type={type} placeholder={placeholder} {...field} />
          </FormControl>
          <FormMessage />
        </FormItem>
      )}
    />
  );
}

interface SelectFieldProps {
  name: FieldName;
  label: string;
  placeholder: string;
  options: readonly string[];
  /** When provided, an explicit empty option is shown with this label. */
  emptyLabel?: string;
}

export function ProfileSelectField({
  name,
  label,
  placeholder,
  options,
  emptyLabel,
}: SelectFieldProps) {
  const { control } = useFormContext<ProfileFormValues>();
  return (
    <FormField
      control={control}
      name={name}
      render={({ field }) => (
        <FormItem>
          <FormLabel>{label}</FormLabel>
          <Select
            value={typeof field.value === "string" ? field.value : ""}
            onValueChange={field.onChange}
          >
            <FormControl>
              <SelectTrigger>
                <SelectValue placeholder={placeholder} />
              </SelectTrigger>
            </FormControl>
            <SelectContent>
              {emptyLabel ? <SelectItem value="">{emptyLabel}</SelectItem> : null}
              {options.map((option) => (
                <SelectItem key={option} value={option}>
                  {option.replace(/-/g, " ")}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <FormMessage />
        </FormItem>
      )}
    />
  );
}

type StatusFieldName = "isStudent" | "isFarmer" | "isMinority" | "isDisabled";

interface YesNoUnsafeFieldProps {
  name: StatusFieldName;
  label: string;
  notSpecifiedLabel: string;
}

export function YesNoUnsafeField({ name, label, notSpecifiedLabel }: YesNoUnsafeFieldProps) {
  const { control } = useFormContext<ProfileFormValues>();
  return (
    <FormField
      control={control}
      name={name}
      render={({ field }) => (
        <FormItem>
          <FormLabel>{label}</FormLabel>
          <Select value={field.value} onValueChange={field.onChange}>
            <FormControl>
              <SelectTrigger>
                <SelectValue placeholder={label} />
              </SelectTrigger>
            </FormControl>
            <SelectContent>
              <SelectItem value="">{notSpecifiedLabel}</SelectItem>
              <SelectItem value="yes">Yes</SelectItem>
              <SelectItem value="no">No</SelectItem>
              <SelectItem value="not-sure">Not sure</SelectItem>
            </SelectContent>
          </Select>
          <FormMessage />
        </FormItem>
      )}
    />
  );
}

export function LanguagesField() {
  const { control } = useFormContext<ProfileFormValues>();
  return (
    <FormField
      control={control}
      name="languages"
      render={({ field }) => (
        <FormItem>
          <FormLabel className="mb-1 block">Languages you can speak</FormLabel>
          <div className="grid gap-2 sm:grid-cols-2">
            {SUPPORTED_UI_LANGUAGES.map((lang) => {
              const checked = field.value.includes(lang.code);
              return (
                <label
                  key={lang.code}
                  className="flex cursor-pointer items-center gap-2 rounded-md border px-3 py-2 text-sm has-[[data-state=checked]]:border-primary"
                >
                  <Checkbox
                    checked={checked}
                    onCheckedChange={() => {
                      const updated = checked
                        ? field.value.filter((code) => code !== lang.code)
                        : [...field.value, lang.code];
                      field.onChange(updated);
                    }}
                  />
                  {lang.native}
                </label>
              );
            })}
          </div>
          <FormMessage />
        </FormItem>
      )}
    />
  );
}

/** Preferred UI/chat language — also mirrors the persisted settings store. */
export function PreferredLanguageField({ label }: { label: string }) {
  const { control } = useFormContext<ProfileFormValues>();
  const setLanguage = useSettingsStore((s) => s.setLanguage);

  const syncUILanguage = (value: string) => {
    const lang = value as LanguageCode;
    if (SUPPORTED_UI_LANGUAGES.some((item) => item.code === lang)) {
      setLanguage(lang);
      void applyUILanguage(lang);
    }
  };

  return (
    <FormField
      control={control}
      name="preferredLanguage"
      render={({ field }) => (
        <FormItem>
          <FormLabel>{label}</FormLabel>
          <Select
            value={field.value}
            onValueChange={(value) => {
              field.onChange(value);
              syncUILanguage(value);
            }}
          >
            <FormControl>
              <SelectTrigger>
                <SelectValue placeholder={label} />
              </SelectTrigger>
            </FormControl>
            <SelectContent>
              {SUPPORTED_UI_LANGUAGES.map((lang) => (
                <SelectItem key={lang.code} value={lang.code}>
                  {lang.native}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <FormMessage />
        </FormItem>
      )}
    />
  );
}
