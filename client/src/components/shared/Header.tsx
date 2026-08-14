import { Menu } from "lucide-react";
import { useTranslation } from "react-i18next";
import { Logo } from "@/components/shared/Logo";
import { NavBar } from "@/components/shared/NavBar";
import { LanguageSwitcher } from "@/components/shared/LanguageSwitcher";
import { VoiceToggle } from "@/components/shared/VoiceToggle";
import { ThemeToggle } from "@/components/shared/ThemeToggle";
import { UserMenu } from "@/components/shared/UserMenu";
import { Button } from "@/components/ui/button";
import { useUiStore } from "@/store/uiSlice";

/** App chrome header: brand, nav, language/voice/theme toggles and user menu. */
export function Header() {
  const { t } = useTranslation();
  const openSidebar = useUiStore((s) => s.openSidebar);

  return (
    <header className="sticky top-0 z-40 w-full border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/80">
      <div className="container flex h-14 items-center gap-2 px-4">
        <Button
          variant="ghost"
          size="icon"
          className="md:hidden"
          aria-label={t("nav.menu")}
          onClick={openSidebar}
        >
          <Menu className="h-5 w-5" />
        </Button>
        <Logo className="mr-4" />
        <NavBar className="flex-1" />
        <div className="ml-auto flex items-center gap-1">
          <LanguageSwitcher />
          <VoiceToggle />
          <ThemeToggle />
          <UserMenu />
        </div>
      </div>
    </header>
  );
}
