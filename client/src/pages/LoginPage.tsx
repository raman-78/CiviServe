import { useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useForm } from "react-hook-form";
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
import {
  Form,
  FormControl,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { Separator } from "@/components/ui/separator";
import { useAuth } from "@/features/auth/AuthContext";
import { firebaseAuthMessage } from "@/features/auth/errors";

interface LoginFormValues {
  email: string;
  password: string;
}

export function LoginPage() {
  const { t } = useTranslation();
  const { signIn, signInWithGoogle } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [submitting, setSubmitting] = useState(false);
  const [googleSubmitting, setGoogleSubmitting] = useState(false);

  const from = (location.state as { from?: { pathname?: string } } | null)?.from?.pathname ?? "/chat";

  const form = useForm<LoginFormValues>({ defaultValues: { email: "", password: "" } });

  const handleSubmit = form.handleSubmit(async ({ email, password }) => {
    setSubmitting(true);
    try {
      await signIn(email, password);
      toast.success(t("auth.welcomeBack"));
      navigate(from, { replace: true });
    } catch (error) {
      toast.error(firebaseAuthMessage(error));
    } finally {
      setSubmitting(false);
    }
  });

  const handleGoogle = async () => {
    setGoogleSubmitting(true);
    try {
      await signInWithGoogle();
      toast.success(t("auth.welcomeBack"));
      navigate(from, { replace: true });
    } catch (error) {
      toast.error(firebaseAuthMessage(error));
    } finally {
      setGoogleSubmitting(false);
    }
  };

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("nav.login")}</CardTitle>
        <CardDescription>{t("auth.loginSubtitle")}</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        <Button
          type="button"
          variant="outline"
          className="w-full"
          disabled={googleSubmitting}
          onClick={handleGoogle}
        >
          {t("auth.continueWithGoogle")}
        </Button>
        <div className="flex items-center gap-3 text-xs text-muted-foreground">
          <Separator className="flex-1" />
          {t("auth.or")}
          <Separator className="flex-1" />
        </div>
        <Form {...form}>
          <form onSubmit={handleSubmit} className="space-y-4">
            <FormField
              control={form.control}
              name="email"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("auth.email")}</FormLabel>
                  <FormControl>
                    <Input type="email" autoComplete="email" placeholder="you@example.com" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <FormField
              control={form.control}
              name="password"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>{t("auth.password")}</FormLabel>
                  <FormControl>
                    <Input type="password" autoComplete="current-password" {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            <div className="flex justify-end">
              <Link to="/forgot-password" className="text-sm text-primary hover:underline">
                {t("auth.forgotPassword")}
              </Link>
            </div>
            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting ? t("common.loading") : t("nav.login")}
            </Button>
          </form>
        </Form>
      </CardContent>
      <CardFooter className="justify-center gap-1 text-sm text-muted-foreground">
        <span>{t("auth.noAccount")}</span>
        <Link to="/register" className="font-medium text-primary hover:underline">
          {t("nav.register")}
        </Link>
      </CardFooter>
    </Card>
  );
}
