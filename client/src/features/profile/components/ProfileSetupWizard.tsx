import { useState } from "react";
import { useForm, type UseFormReturn } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { ArrowLeft, ArrowRight, Check } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Form } from "@/components/ui/form";
import { errorMessage } from "@/lib/errors";
import { INDIAN_STATES } from "@/lib/constants";
import { useSettingsStore } from "@/store/settingsSlice";
import { useAuth } from "@/features/auth/AuthContext";
import { ConsentBanner } from "@/features/profile/components/ConsentBanner";
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
import { updateProfile } from "@/features/profile/api";

const notSpecified = "Not specified";

interface FieldStep {
  titleKey: string;
  fields: (keyof ProfileFormValues)[];
}

const FIELD_STEPS: FieldStep[] = [
  {
    titleKey: "profile.wizard.identity",
    fields: ["name", "phone", "age", "gender", "stateCode", "district"],
  },
  {
    titleKey: "profile.wizard.background",
    fields: [
      "incomeBand",
      "education",
      "occupation",
      "casteCategory",
      "maritalStatus",
      "isStudent",
      "isFarmer",
      "isMinority",
      "isDisabled",
      "disabilityType",
    ],
  },
  {
    titleKey: "profile.wizard.preferences",
    fields: ["languages", "preferredLanguage", "preferredInputMethod", "preferredOutputMethod", "notificationPreference"],
  },
];

const TOTAL_STEPS = 1 + FIELD_STEPS.length + 1; // intro + steps + review

export function ProfileSetupWizard() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { profile, refreshProfile } = useAuth();
  const [step, setStep] = useState(0);
  const [saving, setSaving] = useState(false);

  const consent = useSettingsStore((s) => s.consent);
  const textOnly = useSettingsStore((s) => s.textOnly);
  const highContrast = useSettingsStore((s) => s.highContrast);
  const slowSpeech = useSettingsStore((s) => s.slowSpeech);
  const uiLanguage = useSettingsStore((s) => s.language);

  const form = useForm<ProfileFormValues>({
    resolver: zodResolver(profileSchema),
    defaultValues: (() => {
      const defaults = fromProfile(profile ?? {});
      if (!defaults.preferredLanguage) defaults.preferredLanguage = uiLanguage;
      return defaults;
    })(),
  });

  const isDisabled = form.watch("isDisabled");

  const next = async () => {
    const current = step - 1; // 0-based index into FIELD_STEPS
    const fieldStep = FIELD_STEPS[current];
    if (!fieldStep) return;
    const valid = await form.trigger(fieldStep.fields);
    if (valid) setStep((s) => s + 1);
  };

  const back = () => setStep((s) => s - 1);

  const submit = form.handleSubmit(async (values) => {
    setSaving(true);
    try {
      await updateProfile(
        toProfileUpdate(values, {
          consent,
          accessibility: { textOnly, highContrast, slowSpeech },
        }),
      );
      await refreshProfile();
      toast.success(t("profile.saved"));
      navigate("/profile", { replace: true });
    } catch (error) {
      toast.error(errorMessage(error));
      setSaving(false);
    }
  });

  const progressLabel = step === 0 ? "" : step >= TOTAL_STEPS - 1 ? t("profile.wizard.review") : `${t("profile.wizard.step")} ${step} ${t("profile.wizard.of")} ${TOTAL_STEPS - 1}`;

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("profile.wizard.title")}</CardTitle>
        <CardDescription>{t("profile.wizard.subtitle")}</CardDescription>
        {progressLabel ? (
          <div className="mt-2">
            <div className="mb-1 text-xs font-medium text-muted-foreground">{progressLabel}</div>
            <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
              <div
                className="h-full rounded-full bg-primary transition-all"
                style={{ width: `${(step / (TOTAL_STEPS - 1)) * 100}%` }}
              />
            </div>
          </div>
        ) : null}
      </CardHeader>

      <Form {...form}>
        <form onSubmit={submit}>
          <CardContent>
            {step === 0 ? (
              <div className="space-y-4">
                <p className="text-sm text-muted-foreground">{t("profile.wizard.intro")}</p>
                <ul className="list-inside list-disc space-y-1 text-sm text-muted-foreground">
                  {["identity", "background", "preferences"].map((key) => (
                    <li key={key}>{t(`profile.wizard.${key}`)}</li>
                  ))}
                </ul>
              </div>
            ) : null}

            {step === 1 ? (
              <div className="grid gap-4 sm:grid-cols-2">
                <ProfileInputField name="name" label={t("profile.name")} placeholder={t("profile.name")} />
                <ProfileInputField name="phone" label={t("profile.phone")} type="tel" placeholder="+91 90000 00000" />
                <ProfileInputField name="age" label={t("profile.age")} type="number" placeholder="30" />
                <ProfileSelectField name="gender" label={t("profile.gender")} placeholder={t("profile.gender")} options={GENDERS} emptyLabel={notSpecified} />
                <ProfileSelectField name="stateCode" label={t("profile.state")} placeholder={t("profile.state")} options={INDIAN_STATES.map((s) => s.code)} emptyLabel={notSpecified} />
                <ProfileInputField name="district" label={t("profile.district")} placeholder={t("profile.district")} />
              </div>
            ) : null}

            {step === 2 ? (
              <div className="grid gap-4 sm:grid-cols-2">
                <ProfileSelectField name="incomeBand" label={t("profile.incomeBand")} placeholder={t("profile.incomeBand")} options={INCOME_BANDS} emptyLabel={notSpecified} />
                <ProfileSelectField name="education" label={t("profile.education")} placeholder={t("profile.education")} options={EDUCATION_LEVELS} emptyLabel={notSpecified} />
                <ProfileInputField name="occupation" label={t("profile.occupation")} placeholder={t("profile.occupation")} />
                <ProfileSelectField name="casteCategory" label={t("profile.casteCategory")} placeholder={t("profile.casteCategory")} options={CASTE_CATEGORIES} emptyLabel={notSpecified} />
                <YesNoUnsafeField name="isStudent" label={t("profile.isStudent")} notSpecifiedLabel={notSpecified} />
                <YesNoUnsafeField name="isFarmer" label={t("profile.isFarmer")} notSpecifiedLabel={notSpecified} />
                <YesNoUnsafeField name="isMinority" label={t("profile.isMinority")} notSpecifiedLabel={notSpecified} />
                <YesNoUnsafeField name="isDisabled" label={t("profile.isDisabled")} notSpecifiedLabel={notSpecified} />
                {isDisabled === "yes" ? (
                  <ProfileInputField name="disabilityType" label={t("profile.disabilityType")} placeholder={t("profile.disabilityType")} />
                ) : null}
                <ProfileSelectField name="maritalStatus" label={t("profile.maritalStatus")} placeholder={t("profile.maritalStatus")} options={MARITAL_STATUSES} emptyLabel={notSpecified} />
              </div>
            ) : null}

            {step === 3 ? (
              <div className="space-y-5">
                <div className="grid gap-4 sm:grid-cols-2">
                  <LanguagesField />
                  <PreferredLanguageField label={t("profile.preferredLanguage")} />
                  <ProfileSelectField name="preferredInputMethod" label={t("profile.preferredInputMethod")} placeholder={t("profile.preferredInputMethod")} options={INPUT_OUTPUT_METHODS} emptyLabel={notSpecified} />
                  <ProfileSelectField name="preferredOutputMethod" label={t("profile.preferredOutputMethod")} placeholder={t("profile.preferredOutputMethod")} options={INPUT_OUTPUT_METHODS} emptyLabel={notSpecified} />
                  <ProfileSelectField name="notificationPreference" label={t("profile.notificationPreference")} placeholder={t("profile.notificationPreference")} options={NOTIFICATION_PREFERENCES} emptyLabel={notSpecified} />
                </div>
                <ConsentBanner />
              </div>
            ) : null}

            {step === TOTAL_STEPS - 1 ? <ReviewStep form={form} /> : null}
          </CardContent>

          <CardFooter className="flex items-center justify-between gap-2">
            {step > 0 ? (
              <Button type="button" variant="outline" onClick={back} disabled={saving}>
                <ArrowLeft className="h-4 w-4" />
                {t("common.back")}
              </Button>
            ) : (
              <Button type="button" variant="ghost" onClick={() => navigate("/profile")}>
                {t("profile.wizard.skip")}
              </Button>
            )}
            {step < TOTAL_STEPS - 1 ? (
              <Button type="button" onClick={step === 0 ? () => setStep(1) : () => void next()}>
                {t("common.next")}
                <ArrowRight className="h-4 w-4" />
              </Button>
            ) : (
              <Button type="submit" disabled={saving}>
                {saving ? t("common.loading") : t("profile.wizard.finish")}
                <Check className="h-4 w-4" />
              </Button>
            )}
          </CardFooter>
        </form>
      </Form>
    </Card>
  );
}

function ReviewStep({ form }: { form: UseFormReturn<ProfileFormValues> }) {
  const { t } = useTranslation();
  const values = form.getValues();
  const rows: { label: string; value: string }[] = [
    { label: t("profile.name"), value: values.name },
    { label: t("profile.phone"), value: values.phone },
    { label: t("profile.age"), value: values.age },
    { label: t("profile.gender"), value: values.gender.replace(/-/g, " ") },
    { label: t("profile.state"), value: values.stateCode },
    { label: t("profile.district"), value: values.district },
    { label: t("profile.incomeBand"), value: values.incomeBand.replace(/-/g, " ") },
    { label: t("profile.education"), value: values.education.replace(/-/g, " ") },
    { label: t("profile.casteCategory"), value: values.casteCategory.toUpperCase() },
    { label: t("profile.maritalStatus"), value: values.maritalStatus.replace(/-/g, " ") },
    { label: t("profile.languages"), value: values.languages.join(", ") },
  ].filter((row): row is { label: string; value: string } => Boolean(row.value));

  return (
    <div className="space-y-4">
      <p className="text-sm text-muted-foreground">{t("profile.wizard.reviewDesc")}</p>
      <dl className="grid gap-x-6 gap-y-3 sm:grid-cols-2">
        {rows.map((row) => (
          <div key={row.label} className="flex flex-col">
            <dt className="text-xs uppercase tracking-wide text-muted-foreground">{row.label}</dt>
            <dd className="text-sm font-medium">{row.value}</dd>
          </div>
        ))}
      </dl>
    </div>
  );
}
