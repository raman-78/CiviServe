import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { toast } from "sonner";
import { LogOut, MailCheck, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Separator } from "@/components/ui/separator";
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { useAuth } from "@/features/auth/AuthContext";
import { firebaseAuthMessage } from "@/features/auth/errors";
import { errorMessage } from "@/lib/errors";

/** Account management: identity, email verification, logout-all, deletion. */
export function AccountSettings() {
  const { t } = useTranslation();
  const navigate = useNavigate();
  const { user, me, sendEmailVerification, revokeSessions, deleteAccount } = useAuth();

  const [revoking, setRevoking] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [confirmOpen, setConfirmOpen] = useState(false);

  const email = user?.email ?? me?.email ?? "";
  const displayName = user?.displayName ?? me?.displayName ?? "";
  const emailVerified = user?.emailVerified ?? me?.emailVerified ?? false;

  const handleResendVerification = async () => {
    setVerifying(true);
    try {
      await sendEmailVerification();
      toast.success(t("auth.verificationSent"));
    } catch (error) {
      toast.error(firebaseAuthMessage(error));
    } finally {
      setVerifying(false);
    }
  };

  const handleRevoke = async () => {
    setRevoking(true);
    try {
      await revokeSessions();
      toast.success(t("settings.revoked"));
      navigate("/", { replace: true });
    } catch (error) {
      toast.error(errorMessage(error));
      setRevoking(false);
    }
  };

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await deleteAccount();
      toast.success(t("settings.accountDeleted"));
      navigate("/", { replace: true });
    } catch (error) {
      toast.error(errorMessage(error));
      setDeleting(false);
      setConfirmOpen(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle className="text-lg">{t("settings.account")}</CardTitle>
        <CardDescription>{t("settings.accountDesc")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <div className="flex flex-col gap-1">
          <span className="text-sm font-medium">{displayName || email || t("user.guest")}</span>
          {email ? <span className="text-sm text-muted-foreground">{email}</span> : null}
        </div>

        {email && !emailVerified ? (
          <div className="flex items-center justify-between gap-3 rounded-md border border-dashed p-3">
            <p className="text-sm text-muted-foreground">{t("settings.emailUnverified")}</p>
            <Button size="sm" variant="outline" onClick={() => void handleResendVerification()} disabled={verifying}>
              <MailCheck className="h-4 w-4" />
              {verifying ? t("common.loading") : t("settings.verifyEmail")}
            </Button>
          </div>
        ) : null}

        <Separator />

        <div className="flex items-center justify-between gap-3">
          <div className="space-y-0.5">
            <p className="text-sm font-medium">{t("settings.logoutAll")}</p>
            <p className="text-sm text-muted-foreground">{t("settings.logoutAllDesc")}</p>
          </div>
          <Button variant="outline" onClick={() => void handleRevoke()} disabled={revoking}>
            <LogOut className="h-4 w-4" />
            {revoking ? t("common.loading") : t("settings.logoutAll")}
          </Button>
        </div>

        <Separator />

        <div className="flex items-center justify-between gap-3">
          <div className="space-y-0.5">
            <p className="text-sm font-medium text-destructive">{t("settings.deleteAccount")}</p>
            <p className="text-sm text-muted-foreground">{t("settings.deleteAccountDesc")}</p>
          </div>
          <Dialog open={confirmOpen} onOpenChange={setConfirmOpen}>
            <DialogTrigger asChild>
              <Button variant="destructive" disabled={deleting}>
                <Trash2 className="h-4 w-4" />
                {t("settings.deleteAccount")}
              </Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader>
                <DialogTitle>{t("settings.deleteConfirmTitle")}</DialogTitle>
                <DialogDescription>{t("settings.deleteConfirmDesc")}</DialogDescription>
              </DialogHeader>
              <DialogFooter>
                <Button variant="outline" onClick={() => setConfirmOpen(false)} disabled={deleting}>
                  {t("common.cancel")}
                </Button>
                <Button variant="destructive" onClick={() => void handleDelete()} disabled={deleting}>
                  {deleting ? t("common.loading") : t("common.delete")}
                </Button>
              </DialogFooter>
            </DialogContent>
          </Dialog>
        </div>
      </CardContent>
    </Card>
  );
}
