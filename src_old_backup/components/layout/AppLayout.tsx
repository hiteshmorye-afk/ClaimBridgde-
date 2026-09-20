import React from "react";
import { AppSidebar } from "./AppSidebar";
import { AppHeader } from "./AppHeader";
import { getCurrentUser } from "@/api/auth";

interface AppLayoutProps {
  children: React.ReactNode;
  title?: string;
  breadcrumbs?: Array<{ label: string; href?: string }>;
}

export function AppLayout({ children, title, breadcrumbs }: AppLayoutProps) {
  const user = getCurrentUser();

  return (
    <div className="flex min-h-screen w-full bg-background text-foreground font-sans selection:bg-primary selection:text-white transition-colors duration-200">
      {/* Fixed Left Sidebar */}
      <AppSidebar
        role={user?.role || "Coordinator"}
        userName={user?.name || "23102030"}
        userEmail={user?.email || "23102030@apsit.edu.in"}
      />

      {/* Main Content Area */}
      <div className="flex min-w-0 flex-1 flex-col overflow-x-hidden">
        <AppHeader
          title={title}
          userName={user?.name || "Hospital Coordinator"}
          userRole={user?.role || "Coordinator"}
          breadcrumbs={breadcrumbs}
        />
        <main className="flex-1 p-6 lg:p-8">
          <div className="mx-auto max-w-[1600px]">{children}</div>
        </main>
      </div>
    </div>
  );
}
