import {
  BadgeCheck,
  FileText,
  HelpCircle,
  MapPin,
  MessagesSquare,
  ShieldCheck,
  Sprout,
} from "lucide-react";
import { useTranslation } from "react-i18next";
import { NavLink } from "react-router-dom";
import { useAuth } from "@/features/auth/AuthContext";
import { cn } from "@/lib/utils";

interface NavBarProps {
  className?: string;
  /** Renders vertical (sidebar/drawer) when true, else horizontal. */
  vertical?: boolean;
  onNavigate?: () => void;
}

const NAV_ITEMS = [
  { to: "/chat", key: "nav.chat", icon: MessagesSquare },
  { to: "/eligibility", key: "nav.eligibility", icon: BadgeCheck },
  { to: "/schemes", key: "nav.schemes", icon: Sprout },
  { to: "/centers", key: "nav.centres", icon: MapPin },
  { to: "/documents", key: "nav.documents", icon: FileText },
  { to: "/help", key: "nav.help", icon: HelpCircle },
] as const;

/** Primary app navigation (docs/architecture/07). Admin sees an extra item. */
export function NavBar({ className, vertical, onNavigate }: NavBarProps) {
  const { t } = useTranslation();
  const { me } = useAuth();
  const isAdmin = me?.role === "admin";
  const items = isAdmin
    ? ([...NAV_ITEMS, { to: "/admin", key: "nav.admin", icon: ShieldCheck }] as const)
    : NAV_ITEMS;

  return (
    <nav
      aria-label="Primary"
      className={cn(
        vertical
          ? "flex flex-col gap-1"
          : "hidden items-center gap-1 md:flex",
        className,
      )}
    >
      {items.map(({ to, key, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          onClick={onNavigate}
          className={({ isActive }) =>
            cn(
              "flex items-center gap-2 rounded-md px-3 py-2 text-sm font-medium transition-colors",
              vertical && "w-full",
              isActive
                ? "bg-accent text-accent-foreground"
                : "text-muted-foreground hover:bg-accent/60 hover:text-foreground",
            )
          }
        >
          <Icon className="h-4 w-4 shrink-0" />
          {t(key)}
        </NavLink>
      ))}
    </nav>
  );
}
