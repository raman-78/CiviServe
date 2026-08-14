import { useState } from "react";
import { Navigate, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardFooter,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { useAuth } from "@/features/auth/AuthContext";
import { firebaseAuthMessage } from "@/features/auth/errors";

/** Email-verification prompt shown for unverified accounts (Firebase). */
export function VerifyEmailPage() {
  const { t } = useTranslation();
  const { user, sendEmailVerification } = useAuth();
  const navigate = useNavigate();
  const [sending, setSending] = useState(false);
  const [sent, setSent] = useState(false);

  if (!user) return <Navigate to="/login" replace />;
  if (user.emailVerified) return <Navigate to="/" replace />;

  const handleResend = async () => {
    setSending(true);
    try {
      await sendEmailVerification();
      setSent(true);
      toast.success(t("auth.verificationSent"));
    } catch (error) {
      toast.error(firebaseAuthMessage(error));
    } finally {
      setSending(false);
    }
  };

  const handleCheck = async () => {
    try {
      await user.reload();
      if (user.emailVerified) {
        toast.success(t("auth.verificationVerified"));
        navigate("/", { replace: true });
      } else {
        toast.info(t("auth.verificationPending"));
      }
    } catch (error) {
      toast.error(firebaseAuthMessage(error));
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("auth.verifyTitle")}</CardTitle>
        <CardDescription>
          {t("auth.verifySubtitle")} <span className="font-medium">{user.email}</span>
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <p className="text-sm text-muted-foreground">{t("auth.verifyHint")}</p>
        <Button type="button" variant="outline" className="w-full" disabled={sending} onClick={handleResend}>
          {sending ? t("common.loading") : sent ? t("auth.verificationSent") : t("auth.resendEmail")}
        </Button>
      </CardContent>
      <CardFooter className="flex flex-col gap-2">
        <Button type="button" className="w-full" onClick={handleCheck}>
          {t("auth.iVerified")}
        </Button>
      </CardFooter>
    </Card>
  );
}
