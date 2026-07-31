import { Menu, Moon, Sun, LogOut, ShieldCheck } from "lucide-react";
import { Button } from "../ui/button";
import { Badge } from "../ui/badge";
import { ROLE_META } from "../../lib/status";
import { useAuth } from "../../context/AuthContext";
import { useTheme } from "../../hooks/use-theme";

export function Topbar({ onMenuClick }) {
  const { user, logout } = useAuth();
  const { theme, toggleTheme } = useTheme();
  const roleMeta = ROLE_META[user?.role] || { label: user?.role, variant: "secondary" };

  return (
    <header className="sticky top-0 z-30 flex h-16 items-center justify-between gap-4 border-b bg-background/80 px-4 backdrop-blur-sm sm:px-6">
      <div className="flex items-center gap-3">
        <Button variant="ghost" size="icon" className="lg:hidden" onClick={onMenuClick}>
          <Menu className="h-5 w-5" />
        </Button>
        <div className="hidden items-center gap-2 sm:flex">
          <span className="text-sm text-muted-foreground">Environment</span>
          <Badge variant="success">Production</Badge>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <Button variant="ghost" size="icon" onClick={toggleTheme} aria-label="Toggle theme">
          {theme === "dark" ? <Sun className="h-4 w-4" /> : <Moon className="h-4 w-4" />}
        </Button>
        <div className="mx-2 hidden h-6 w-px bg-border sm:block" />
        <div className="flex items-center gap-2.5">
          <div className="flex h-8 w-8 items-center justify-center rounded-full bg-primary/10 text-primary">
            <ShieldCheck className="h-4 w-4" />
          </div>
          <div className="hidden text-left sm:block">
            <p className="text-sm font-medium leading-none">{user?.username}</p>
            <Badge variant={roleMeta.variant} className="mt-1">
              {roleMeta.label}
            </Badge>
          </div>
        </div>
        <Button variant="ghost" size="icon" onClick={() => logout()} aria-label="Sign out">
          <LogOut className="h-4 w-4" />
        </Button>
      </div>
    </header>
  );
}
