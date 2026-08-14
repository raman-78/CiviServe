import { useTranslation } from "react-i18next";
import { NavBar } from "@/components/shared/NavBar";
import { Sheet, SheetContent, SheetTitle } from "@/components/ui/sheet";
import { useUiStore } from "@/store/uiSlice";

/** Mobile navigation drawer rendered from the header's menu button. */
export function MobileNav() {
  const { t } = useTranslation();
  const sidebarOpen = useUiStore((s) => s.sidebarOpen);
  const closeSidebar = useUiStore((s) => s.closeSidebar);

  return (
    <Sheet open={sidebarOpen} onOpenChange={(open) => (open ? undefined : closeSidebar())}>
      <SheetContent side="left" className="w-72 p-4">
        <SheetTitle className="sr-only">{t("nav.menu")}</SheetTitle>
        <NavBar vertical onNavigate={closeSidebar} />
      </SheetContent>
    </Sheet>
  );
}
