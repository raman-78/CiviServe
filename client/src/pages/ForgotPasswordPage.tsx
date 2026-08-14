import { useState } from "react";
import { Link } from "react-router-dom";
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
import { useAuth } from "@/features/auth/AuthContext";
import { firebaseAuthMessage } from "@/features/auth/errors";

interface ForgotPasswordFormValues {
  email: string;
}

export function ForgotPasswordPage() {
  const { t } = useTranslation();
  const { sendPasswordReset } = useAuth();
  const [submitting, setSubmitting] = useState(false);

  const form = useForm<ForgotPasswordFormValues>({ defaultValues: { email: "" } });

  const handleSubmit = form.handleSubmit(async ({ email }) => {
    setSubmitting(true);
    try {
      await sendPasswordReset(email);
      toast.success(t("auth.resetSent"));
      form.reset();
    } catch (error) {
      toast.error(firebaseAuthMessage(error));
    } finally {
      setSubmitting(false);
    }
  });

  return (
    <Card>
      <CardHeader>
        <CardTitle>{t("auth.resetTitle")}</CardTitle>
        <CardDescription>{t("auth.resetSubtitle")}</CardDescription>
      </CardHeader>
      <CardContent>
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
            <Button type="submit" className="w-full" disabled={submitting}>
              {submitting ? t("common.loading") : t("auth.sendReset")}
            </Button>
          </form>
        </Form>
      </CardContent>
      <CardFooter className="justify-center text-sm text-muted-foreground">
        <Link to="/login" className="font-medium text-primary hover:underline">
          {t("nav.login")}
        </Link>
      </CardFooter>
    </Card>
  );
}
