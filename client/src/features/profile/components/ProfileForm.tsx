import { useState } from "react";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import type { UserProfile } from "@schemesathi/shared";
import { Button } from "@/components/ui/button";
import { Form } from "@/components/ui/form";
import { errorMessage } from "@/lib/errors";
import { useSettingsStore } from "@/store/settingsSlice";
import { updateProfile } from "@/features/profile/api";
import {
  CASTE_CATEGORIES,
  EDUCATION_LEVELS,
  GENDERS,
  INCOME_BANDS,
  INPUT_OUTPUT_METHODS,
  MARITAL_STATUSES,
  NOTIFICATION_PREFERENCES,
  type ProfileFormValues,
  fromProfile,
  profileSchema,
  toProfileUpdate,
} from "@/features/profile/profileSchema";
import {
  LanguagesField,
  PreferredLanguageField,
  ProfileInputField,
  ProfileSelectField,
  YesNoUnsafeField,
} from "@/features/profile/components/ProfileFields";
import { INDIAN_STATES } from "@/lib/constants";

interface ProfileFormProps {
  defaultValues?: Partial<ProfileFormValues>;
  onSaved?: (profile: UserProfile) => void;
}

const notSpecified = "Not specified";

/** Full citizen profile form, shared by /profile/edit and the setup wizard. */
export function ProfileForm({ defaultValues, onSaved }: ProfileFormProps) {
  const { t } = useTranslation();
  const [saving, setSaving] = useState(false);

  const consent = useSettingsStore((s) => s.consent);
  const textOnly = useSettingsStore((s) => s.textOnly);
  const highContrast = useSettingsStore((s) => s.highContrast);
  const slowSpeech = useSettingsStore((s) => s.slowSpeech);

  const form = useForm<ProfileFormValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: { ...fromProfile({}), ...defaultValues },
  });

  const isDisabled = form.watch("isDisabled");

  const handleSubmit = form.handleSubmit(async (values) => {
    setSaving(true);
    try {
      const saved = await updateProfile(
        toProfileUpdate(values, {
          consent,
          accessibility: { textOnly, highContrast, slowSpeech },
        }),
      );
      toast.success(t("profile.saved"));
      onSaved?.(saved);
    } catch (error) {
      toast.error(errorMessage(error));
    } finally {
      setSaving(false);
    }
  });

  return (
    <Form {...form}>
      <form onSubmit={handleSubmit} className="space-y-6">
        <fieldset className="space-y-4" disabled={saving}>
          <h3 className="text-sm font-medium text-muted-foreground">{t("profile.sectionIdentity")}</h3>
          <div className="grid gap-4 sm:grid-cols-2">
            <ProfileInputField name="name" label={t("profile.name")} placeholder={t("profile.name")} />
            <ProfileInputField name="phone" label={t("profile.phone")} type="tel" placeholder="+91 90000 00000" />
            <ProfileInputField name="age" label={t("profile.age")} type="number" placeholder="30" />
            <ProfileSelectField
              name="gender"
              label={t("profile.gender")}
              placeholder={t("profile.gender")}
              options={GENDERS}
              emptyLabel={notSpecified}
            />
          </div>

          <h3 className="text-sm font-medium text-muted-foreground">{t("profile.sectionLocation")}</h3>
          <div className="grid gap-4 sm:grid-cols-2">
            <ProfileSelectField
              name="stateCode"
              label={t("profile.state")}
              placeholder={t("profile.state")}
              options={INDIAN_STATES.map((state) => state.code)}
              emptyLabel={notSpecified}
            />
            <ProfileInputField name="district" label={t("profile.district")} placeholder={t("profile.district")} />
          </div>

          <h3 className="text-sm font-medium text-muted-foreground">{t("profile.sectionIncome")}</h3>
          <div className="grid gap-4 sm:grid-cols-2">
            <ProfileSelectField
              name="incomeBand"
              label={t("profile.incomeBand")}
              placeholder={t("profile.incomeBand")}
              options={INCOME_BANDS}
              emptyLabel={notSpecified}
            />
            <ProfileSelectField
              name="education"
              label={t("profile.education")}
              placeholder={t("profile.education")}
              options={EDUCATION_LEVELS}
              emptyLabel={notSpecified}
            />
            <ProfileInputField name="occupation" label={t("profile.occupation")} placeholder={t("profile.occupation")} />
            <ProfileSelectField
              name="casteCategory"
              label={t("profile.casteCategory")}
              placeholder={t("profile.casteCategory")}
              options={CASTE_CATEGORIES}
              emptyLabel={notSpecified}
            />
          </div>

          <h3 className="text-sm font-medium text-muted-foreground">{t("profile.sectionStatus")}</h3>
          <div className="grid gap-4 sm:grid-cols-2">
            <YesNoUnsafeField name="isStudent" label={t("profile.isStudent")} notSpecifiedLabel={notSpecified} />
            <YesNoUnsafeField name="isFarmer" label={t("profile.isFarmer")} notSpecifiedLabel={notSpecified} />
            <YesNoUnsafeField name="isMinority" label={t("profile.isMinority")} notSpecifiedLabel={notSpecified} />
            <YesNoUnsafeField name="isDisabled" label={t("profile.isDisabled")} notSpecifiedLabel={notSpecified} />
            {isDisabled === "yes" ? (
              <ProfileInputField name="disabilityType" label={t("profile.disabilityType")} placeholder={t("profile.disabilityType")} />
            ) : null}
            <ProfileSelectField
              name="maritalStatus"
              label={t("profile.maritalStatus")}
              placeholder={t("profile.maritalStatus")}
              options={MARITAL_STATUSES}
              emptyLabel={notSpecified}
            />
          </div>

          <h3 className="text-sm font-medium text-muted-foreground">{t("profile.sectionPreferences")}</h3>
          <div className="grid gap-4 sm:grid-cols-2">
            <LanguagesField />
            <PreferredLanguageField label={t("profile.preferredLanguage")} />
            <ProfileSelectField
              name="preferredInputMethod"
              label={t("profile.preferredInputMethod")}
              placeholder={t("profile.preferredInputMethod")}
              options={INPUT_OUTPUT_METHODS}
              emptyLabel={notSpecified}
            />
            <ProfileSelectField
              name="preferredOutputMethod"
              label={t("profile.preferredOutputMethod")}
              placeholder={t("profile.preferredOutputMethod")}
              options={INPUT_OUTPUT_METHODS}
              emptyLabel={notSpecified}
            />
            <ProfileSelectField
              name="notificationPreference"
              label={t("profile.notificationPreference")}
              placeholder={t("profile.notificationPreference")}
              options={NOTIFICATION_PREFERENCES}
              emptyLabel={notSpecified}
            />
          </div>
        </fieldset>
        <div className="flex justify-end">
          <Button type="submit" disabled={saving}>
            {saving ? t("common.loading") : t("common.save")}
          </Button>
        </div>
      </form>
    </Form>
  );
}
