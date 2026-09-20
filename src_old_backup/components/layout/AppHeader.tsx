import React, { useState } from "react";
import { Search, Bell, ShieldCheck, ChevronRight, Activity, Command, Sun, Moon } from "lucide-react";
import { Link } from "@tanstack/react-router";
import { useTheme } from "@/hooks/useTheme";

interface AppHeaderProps {
  title?: string;
  subtitle?: string;
  userName?: string;
  userRole?: string;
  breadcrumbs?: Array<{ label: string; href?: string }>;
}

export function AppHeader({
  title = "Claims Operations Center",
  subtitle = "Real-time Verification, OCR Extraction & Policy Readiness",
  userName = "Hospital Coordinator",
  userRole = "Coordinator",
  breadcrumbs = [{ label: "Dashboard", href: "/" }],
}: AppHeaderProps) {
  const [searchQuery, setSearchQuery] = useState("");
  const { theme, toggleTheme, isDark } = useTheme();

  return (
    <header className="sticky top-0 z-20 flex h-16 w-full items-center justify-between border-b border-border bg-card/90 px-6 backdrop-blur-md">
      
      {/* BREADCRUMBS & TITLE */}
      <div className="flex items-center gap-3">
        <nav className="flex items-center gap-1.5 text-xs text-muted-foreground">
          {breadcrumbs.map((b, idx) => (
            <React.Fragment key={b.label}>
              {idx > 0 && <ChevronRight className="size-3 text-muted-foreground/60" />}
              {b.href ? (
                <Link to={b.href as any} className="transition hover:text-foreground">
                  {b.label}
                </Link>
              ) : (
                <span className="font-semibold text-foreground">{b.label}</span>
              )}
            </React.Fragment>
          ))}
        </nav>
      </div>

      {/* GLOBAL SEARCH BAR */}
      <div className="relative hidden w-96 md:block">
        <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
        <input
          type="search"
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          placeholder="Search claims, patients, policies, ICD codes..."
          className="h-9 w-full rounded-xl border border-border bg-background pl-9 pr-10 text-xs text-foreground placeholder-muted-foreground outline-none transition focus:border-primary focus:ring-1 focus:ring-primary"
        />
        <div className="absolute right-2.5 top-1/2 flex -translate-y-1/2 items-center gap-0.5 rounded border border-border bg-muted/60 px-1.5 py-0.5 text-[10px] font-mono text-muted-foreground">
          <Command className="size-2.5" /> K
        </div>
      </div>

      {/* LIGHT/DARK TOGGLE, SYSTEM STATUS, NOTIFICATIONS & ROLE BADGE */}
      <div className="flex items-center gap-3">
        
        {/* Theme Toggle Button */}
        <button
          type="button"
          onClick={toggleTheme}
          title={`Switch to ${isDark ? "Light Mode" : "Dark Mode"}`}
          className="flex size-9 items-center justify-center rounded-xl border border-border bg-background text-foreground transition hover:border-primary hover:text-primary shadow-sm"
        >
          {isDark ? <Sun className="size-4 text-amber-400" /> : <Moon className="size-4 text-slate-700" />}
        </button>

        {/* Notifications */}
        <button
          type="button"
          aria-label="Notifications"
          className="relative flex size-9 items-center justify-center rounded-xl border border-border bg-background text-muted-foreground transition hover:border-primary hover:text-foreground shadow-sm"
        >
          <Bell className="size-4" />
          <span className="absolute -right-1 -top-1 flex size-4 items-center justify-center rounded-full bg-primary text-[9px] font-bold text-white">
            3
          </span>
        </button>

        {/* Role & User Badge */}
        <div className="flex items-center gap-2.5 border-l border-border pl-3">
          <div className="flex size-8 items-center justify-center rounded-lg bg-gradient-to-br from-primary to-accent text-xs font-bold text-white">
            {userName.charAt(0).toUpperCase()}
          </div>
          <div className="hidden text-left sm:block">
            <p className="text-xs font-semibold leading-none text-foreground">{userName}</p>
            <p className="mt-1 text-[10px] text-accent font-semibold">{userRole}</p>
          </div>
        </div>

      </div>

    </header>
  );
}