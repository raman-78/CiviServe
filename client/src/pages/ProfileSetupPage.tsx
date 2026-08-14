import { ProfileSetupWizard } from "@/features/profile/components/ProfileSetupWizard";

/** Onboarding wizard for citizens who have not completed their profile. */
export function ProfileSetupPage() {
  return (
    <div className="mx-auto max-w-3xl">
      <ProfileSetupWizard />
    </div>
  );
}
