import { NavLink } from "react-router-dom";
import {
  LayoutDashboard,
  ShieldCheck,
  ClipboardCheck,
  ScrollText,
  FlaskConical,
  BarChart3,
  Sparkles,
  Settings,
  X,
  MessageSquare,
} from "lucide-react";
import { cn } from "../../lib/utils";
import { useAuth } from "../../context/AuthContext";
import { Button } from "../ui/button";

const NAV_GROUPS = [
  {
    label: "Operations",
    items: [
      { to: "/", label: "Dashboard", icon: LayoutDashboard, end: true },
      { to: "/policies", label: "Policies", icon: ShieldCheck, roles: ["viewer"] },
      { to: "/approvals", label: "Approvals", icon: ClipboardCheck, roles: ["auditor"] },
      // { to: "/runtime", label: "Runtime Monitor", icon: Activity, roles: ["viewer"] },
      { to: "/audit", label: "Audit Center", icon: ScrollText, roles: ["auditor"] },
      { to: "/settings", label: "Settings", icon: Settings, roles: ["viewer"] },
    ],
  },
  {
    label: "Intelligence",
    items: [
      { to: "/chat", label: "AI Chatbot", icon: MessageSquare, roles: ["viewer"] },
      { to: "/simulation", label: "Simulation", icon: FlaskConical, roles: ["operator"] },
      { to: "/analytics", label: "Analytics", icon: BarChart3, roles: ["auditor"] },
      // { to: "/architecture", label: "Architecture", icon: Network, roles: ["viewer"] },
      { to: "/ai", label: "AI Explainability", icon: Sparkles, roles: ["auditor"] },
    ],
  },
];

export function Sidebar({ open, onClose }) {
  const { hasRole } = useAuth();

  return (
    <>
      {open && (
        <div
          className="fixed inset-0 z-40 bg-black/50 lg:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 flex w-64 flex-col border-r border-border bg-sidebar text-sidebar-foreground transition-transform duration-200 lg:translate-x-0",
          open ? "translate-x-0" : "-translate-x-full"
        )}
      >
        <div className="flex h-16 items-center justify-between border-b border-white/5 px-5">
          <div className="flex items-center gap-2.5">
            <div className="flex h-8 w-8 items-center justify-center rounded-md bg-primary">
              <ShieldCheck className="h-4.5 w-4.5 text-primary-foreground" />
            </div>
            <div>
              <p className="text-sm font-semibold leading-none">Aegis AI</p>
              <p className="mt-0.5 text-[10px] uppercase tracking-wider text-sidebar-foreground/50">
                Runtime Governance
              </p>
            </div>
          </div>
          <Button variant="ghost" size="icon" className="text-sidebar-foreground lg:hidden" onClick={onClose}>
            <X className="h-4 w-4" />
          </Button>
        </div>

        <nav className="flex-1 space-y-6 overflow-y-auto px-3 py-4 scrollbar-thin">
          {NAV_GROUPS.map((group) => {
            const items = group.items.filter((item) => !item.roles || hasRole(item.roles[0]));
            if (items.length === 0) return null;
            return (
              <div key={group.label}>
                <p className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-wider text-sidebar-foreground/40">
                  {group.label}
                </p>
                <ul className="space-y-1">
                  {items.map((item) => (
                    <li key={item.to}>
                      <NavLink
                        to={item.to}
                        end={item.end}
                        onClick={onClose}
                        className={({ isActive }) =>
                          cn(
                            "flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-sidebar-foreground/80 transition-colors hover:bg-sidebar-muted hover:text-sidebar-foreground",
                            isActive && "bg-sidebar-muted text-sidebar-foreground"
                          )
                        }
                      >
                        <item.icon className="h-4 w-4 shrink-0" />
                        {item.label}
                      </NavLink>
                    </li>
                  ))}
                </ul>
              </div>
            );
          })}
        </nav>

        <div className="border-t border-white/5 p-4 text-[10px] leading-relaxed text-sidebar-foreground/40">
          Enterprise AI Runtime
          <br />
          Governance Platform · v1.0.0
        </div>
      </aside>
    </>
  );
}
