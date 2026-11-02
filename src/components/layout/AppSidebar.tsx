import React from "react";
import { Link, useRouterState } from "@tanstack/react-router";
import {
  LayoutDashboard,
  FileSpreadsheet,
  FileText,
  UserCheck,
  BarChart3,
  FileCheck,
  Settings,
  Plus,
  ShieldCheck,
  LogOut,
  CircleUserRound,
  HelpCircle,
  BellRing,
  Building2,
  ClipboardList,
  Stethoscope,
  FileClock,
  ClipboardCheck,
  Pill,
  LaptopMinimalCheck,
  ClipboardPlus,
  UserRound,
  Sun,
  Moon,
  type LucideIcon,
} from "lucide-react";
import { logoutUser, getCurrentUser } from "@/api/auth";
import { useTheme } from "@/hooks/useTheme";

interface AppSidebarProps {
  role?: string;
  userName?: string;
  userEmail?: string;
  onLogout?: () => void;
}

interface NavigationItem {
  label: string;
  href: string;
  icon: LucideIcon;
  highlight?: boolean;
  isAction?: boolean;
  badge?: string;
}

interface SidebarSection {
  title: string;
  items: NavigationItem[];
}

function normalizeRole(role?: string): string {
  const normalized = (role || "").trim().toLowerCase();
  const aliases: Record<string, string> = {
    admin: "admin",
    administrator: "admin",
    claimant: "claimant",
    patient: "claimant",
    user: "claimant",
    "hospital_coordinator": "hospital_coordinator",
    "hospital coordinator": "hospital_coordinator",
    coordinator: "hospital_coordinator",
    "claim_officer": "claim_officer",
    "claims_officer": "claim_officer",
    "claim officer": "claim_officer",
    "claims officer": "claim_officer",
    "tpa_reviewer": "claim_officer",
    "tpa reviewer": "claim_officer",
    reviewer: "claim_officer",
  };

  return aliases[normalized] || normalized;
}

function getSidebarRole(role?: string): "claimant" | "hospital_coordinator" | "claim_officer" | "admin" {
  const normalized = normalizeRole(role);

  if (normalized === "admin") return "admin";
  if (["claim_officer", "claims_officer", "tpa_reviewer", "reviewer"].includes(normalized)) return "claim_officer";
  if (["hospital_coordinator", "hospital coordinator", "coordinator"].includes(normalized)) return "hospital_coordinator";
  return "claimant";
}

export function AppSidebar({
  role = "claimant",
  userName = "Claimant",
  userEmail = "claimant@example.com",
  onLogout,
}: AppSidebarProps) {
  const routerState = useRouterState();
  const currentPath = routerState.location.pathname;
  const { toggleTheme, isDark } = useTheme();

  const [mounted, setMounted] = React.useState(false);
  React.useEffect(() => {
    setMounted(true);
  }, []);

  const user = mounted ? getCurrentUser() : null;
  const sidebarRole = getSidebarRole(user?.canonical_role || user?.role || role);

  const isActiveItem = (href: string) => {
    if (href === "/claim-readiness") {
      return currentPath === "/claim-readiness" || currentPath.startsWith("/claim-readiness");
    }
    if (href === "/claims") {
      return (currentPath === "/claims" || currentPath.startsWith("/claims/")) && !currentPath.startsWith("/claims/new");
    }
    if (href === "/") {
      return currentPath === "/";
    }
    return currentPath === href || currentPath.startsWith(`${href}/`);
  };

  const patientSections: SidebarSection[] = [
    {
      title: "Claim Operations",
      items: [
        { label: "Pre-Authorization", href: "/claims/new", icon: ClipboardList },
        { label: "My Claims", href: "/claims", icon: ZapIcon, highlight: true },
        { label: "Overall Claim Readiness", href: "/claim-readiness", icon: ClipboardCheck },
        { label: "Add Claim", href: "/claims/new", icon: Plus, isAction: true },
        { label: "Documents", href: "/documents", icon: FileText },
      ],
    },
    {
      title: "Account",
      items: [
        { label: "My Profile", href: "/profile", icon: CircleUserRound },
        { label: "Settings", href: "/settings", icon: Settings },
        { label: "Help & Support", href: "/support", icon: HelpCircle },
      ],
    },
  ];

  const hospitalSections: SidebarSection[] = [
    {
      title: "Hospital Operations",
      items: [
        { label: "Dashboard", href: "/", icon: LayoutDashboard },
        { label: "New Cashless Request", href: "/claims/new", icon: ClipboardPlus },
        { label: "Patient Records", href: "/claims", icon: UserRound },
        { label: "Overall Claim Readiness", href: "/claim-readiness", icon: ClipboardCheck },
        { label: "Pre-Authorization", href: "/claims", icon: ClipboardList },
        { label: "Treatment Updates", href: "/claims", icon: Stethoscope },
        { label: "Final Authorization", href: "/claims", icon: ClipboardCheck },
        { label: "Discharge Readiness", href: "/claims", icon: FileClock },
        { label: "Documents", href: "/documents", icon: FileText },
        { label: "Reports", href: "/reports", icon: FileCheck },
      ],
    },
  ];

  const tpaSections: SidebarSection[] = [
    {
      title: "Claim Adjudication",
      items: [
        { label: "Dashboard", href: "/", icon: LayoutDashboard },
        { label: "Review Queue", href: "/review", icon: UserCheck },
        { label: "Pending Claims", href: "/review", icon: FileSpreadsheet },
        { label: "Overall Claim Readiness", href: "/claim-readiness", icon: ClipboardCheck },
        { label: "Document Verification", href: "/documents", icon: FileText },
        { label: "Medical Review", href: "/ai-analysis", icon: Stethoscope },
        { label: "Policy Validation", href: "/ai-analysis", icon: ShieldCheck },
        { label: "Queries", href: "/review", icon: BellRing },
        { label: "Approved Claims", href: "/claims", icon: FileCheck },
        { label: "Rejected Claims", href: "/claims", icon: FileCheck },
        { label: "Reports", href: "/reports", icon: BarChart3 },
      ],
    },
  ];

  const adminSections: SidebarSection[] = [
    {
      title: "Administration",
      items: [
        { label: "Dashboard", href: "/", icon: LayoutDashboard },
        { label: "Claims", href: "/claims", icon: FileSpreadsheet },
        { label: "Overall Claim Readiness", href: "/claim-readiness", icon: ClipboardCheck },
        { label: "Review Queue", href: "/review", icon: UserCheck },
        { label: "Documents", href: "/documents", icon: FileText },
        { label: "Analytics", href: "/analytics", icon: BarChart3 },
        { label: "Reports", href: "/reports", icon: FileCheck },
        { label: "Settings", href: "/settings", icon: Settings },
      ],
    },
  ];

  const sections: SidebarSection[] =
    sidebarRole === "claim_officer"
      ? tpaSections
      : sidebarRole === "hospital_coordinator"
      ? hospitalSections
      : patientSections;

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
      <div className="flex h-16 items-center justify-between border-b border-border px-5">
        <Link to={sidebarRole === "claimant" ? "/claims" : "/"} className="flex min-w-0 items-center gap-2.5 group">
          <div className="flex size-9 items-center justify-center rounded-xl bg-gradient-to-br from-primary to-accent shadow-md group-hover:scale-105 transition-transform">
            <ShieldCheck className="size-5 text-white" />
          </div>
          <div className="min-w-0">
            <span className="text-lg font-bold tracking-tight text-foreground whitespace-nowrap">
              Claim<span className="text-primary">Bridge</span>
            </span>
          </div>
        </Link>
      </div>

      <div className="flex-1 overflow-y-auto px-3 py-4 space-y-4">
        {sections.map((section) => (
          <div key={section.title} className="space-y-1">
            <div className="px-3 pb-2 text-[10px] font-semibold uppercase tracking-wider text-muted-foreground">
              {section.title}
            </div>

            {section.items.map((item) => {
              const Icon = item.icon;
              const isActive = isActiveItem(item.href);

              return (
                <Link
                  key={item.label}
                  to={item.href as any}
                  className={`group flex min-w-0 items-center justify-between rounded-xl px-3 py-2.5 text-xs font-medium transition-all duration-200 ${
                    isActive
                      ? "bg-primary/10 text-primary border border-primary/40 font-bold shadow-sm"
                      : item.isAction
                      ? "bg-primary text-white hover:bg-primary/90 shadow-md"
                      : "text-muted-foreground hover:bg-muted hover:text-foreground"
                  }`}
                >
                  <div className="flex min-w-0 items-center gap-2.5">
                    <Icon
                      className={`size-4 shrink-0 transition-colors ${
                        isActive
                          ? "text-primary"
                          : item.isAction
                          ? "text-white"
                          : "text-muted-foreground group-hover:text-foreground"
                      }`}
                    />
                    <span className="truncate">{item.label}</span>
                  </div>

                  {item.badge && (
                    <span className="rounded-full bg-muted px-2 py-0.5 text-[10px] font-mono font-semibold text-muted-foreground">
                      {item.badge}
                    </span>
                  )}
                </Link>
              );
            })}
          </div>
        ))}
      </div>

      <div className="border-t border-border bg-sidebar p-4 space-y-2">
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
          Logout
        </button>
      </div>
    </aside>
  );
}

function ZapIcon(props: React.ComponentProps<typeof LayoutDashboard>) {
  return <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" {...props}><path d="M13 2 4 14h6l-1 8 9-12h-6l1-8Z" /></svg>;
}