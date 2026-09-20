import React from "react";
import { Link, useRouterState } from "@tanstack/react-router";
import {
  LayoutDashboard,
  FileSpreadsheet,
  FileText,
  BrainCircuit,
  Zap,
  UserCheck,
  Link2,
  BarChart3,
  FileCheck,
  Settings,
  Plus,
  ShieldCheck,
  LogOut,
  Sparkles,
  Sun,
  Moon,
} from "lucide-react";
import { logoutUser, getCurrentUser } from "@/api/auth";
import { useTheme } from "@/hooks/useTheme";

interface AppSidebarProps {
  role?: string;
  userName?: string;
  userEmail?: string;
  onLogout?: () => void;
}

export function AppSidebar({
  role = "Coordinator",
  userName = "23102030",
  userEmail = "23102030@apsit.edu.in",
  onLogout,
}: AppSidebarProps) {
  const routerState = useRouterState();
  const currentPath = routerState.location.pathname;
  const { theme, toggleTheme, isDark } = useTheme();

  const user = getCurrentUser();
  const activeRole = user?.role || role || "Coordinator";
  const activeName = user?.name || userName || "23102030";
  const activeEmail = user?.email || userEmail || "23102030@apsit.edu.in";
  const isHospitalUser = (user?.portal || "Hospital") === "Hospital";

  const allNav = [
    { label: "Dashboard", href: "/", icon: LayoutDashboard, tpaOnly: true },
    { label: "Claims", href: "/claims", icon: FileSpreadsheet, badge: "28,218" },
    { label: "New Claim", href: "/claims/new", icon: Plus, isAction: true },
    { label: "Documents", href: "/documents", icon: FileText },
    { label: "AI Analysis", href: "/ai-analysis", icon: BrainCircuit, badge: "AI Core" },
    { label: "Claim Readiness", href: "/claims/CLM-TEST-001", icon: Zap, highlight: true },
    { label: "Human Review", href: "/review", icon: UserCheck, badge: "342" },
    { label: "TPA / Pre-Auth", href: "/tpa-integration", icon: Link2, placeholder: true, tpaOnly: true },
    { label: "Analytics", href: "/analytics", icon: BarChart3, tpaOnly: true },
    { label: "Reports", href: "/reports", icon: FileCheck },
    { label: "Settings", href: "/settings", icon: Settings },
  ];

  const mainNav = allNav.filter((item) => !isHospitalUser || !item.tpaOnly);

  const handleSignOut = () => {
    logoutUser();
    if (onLogout) {
      onLogout();
    } else {
      window.location.href = "/auth";
    }
  };

  return (
    <aside className="sticky top-0 z-30 flex h-screen w-64 shrink-0 flex-col border-r border-border bg-sidebar text-sidebar-foreground select-none">
      
      {/* BRAND LOCKUP */}
      <div className="flex h-16 items-center justify-between border-b border-border px-5">
        <Link to={isHospitalUser ? "/claims" : "/"} className="flex items-center gap-2.5 group">
          <div className="flex size-9 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-accent shadow-md group-hover:scale-105 transition-transform">
            <ShieldCheck className="size-5 text-white" />
          </div>
          <div>
            <span className="text-lg font-bold tracking-tight text-foreground">
              Claim<span className="text-primary">Bridge</span>
            </span>
          </div>
        </Link>
      </div>

      {/* NAVIGATION LINKS */}
      <div className="flex-1 overflow-y-auto px-3 py-4 space-y-1">
        
        <div className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
          Dashboard
        </div>

        {mainNav.map((item) => {
          const Icon = item.icon;
          const isActive = currentPath === item.href;

          return (
            <Link
              key={item.label}
              to={item.href as any}
              className={`group flex items-center justify-between rounded-xl px-3 py-2.5 text-xs font-medium transition-all duration-200 ${
                isActive
                  ? "bg-primary/10 text-primary border border-primary/40 font-bold shadow-sm"
                  : item.isAction
                  ? "bg-primary text-white hover:bg-primary/90 shadow-md"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              }`}
            >
              <div className="flex items-center gap-2.5">
                <Icon
                  className={`size-4 transition-colors ${
                    isActive
                      ? "text-primary"
                      : item.highlight
                      ? "text-accent"
                      : item.isAction
                      ? "text-white"
                      : "text-muted-foreground group-hover:text-foreground"
                  }`}
                />
                <span>{item.label}</span>
              </div>

              {item.badge && (
                <span
                  className={`rounded-full px-2 py-0.5 text-[10px] font-mono font-semibold ${
                    item.badge === "AI Core"
                      ? "bg-purple-500/20 text-purple-600 dark:text-purple-400"
                      : "bg-muted text-muted-foreground"
                  }`}
                >
                  {item.badge}
                </span>
              )}

              {item.placeholder && (
                <span className="rounded-full bg-amber-500/10 px-1.5 py-0.5 text-[9px] font-mono text-amber-600 dark:text-amber-400">
                  Pending
                </span>
              )}
            </Link>
          );
        })}
      </div>

      {/* FOOTER & THEME SWITCH */}
      <div className="border-t border-border p-4 bg-sidebar space-y-2">
        
        <button
          type="button"
          onClick={toggleTheme}
          className="flex w-full items-center justify-center gap-2 rounded-lg border border-border bg-card py-2 text-xs font-semibold text-muted-foreground transition hover:border-primary hover:text-foreground"
        >
          {isDark ? <Sun className="size-3.5 text-amber-400" /> : <Moon className="size-3.5 text-slate-700" />}
          <span>{isDark ? "Light Mode" : "Dark Mode"}</span>
        </button>

        <button
          type="button"
          onClick={handleSignOut}
          className="flex w-full items-center justify-center gap-2 rounded-lg border border-border bg-card py-2 text-xs font-semibold text-muted-foreground transition hover:border-red-500/50 hover:bg-red-500/10 hover:text-red-500"
        >
          <LogOut className="size-3.5" />
          Sign Out Portal
        </button>
      </div>

    </aside>
  );
}