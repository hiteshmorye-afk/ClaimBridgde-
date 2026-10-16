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
  const [mounted, setMounted] = React.useState(false);

  React.useEffect(() => {
    setMounted(true);
  }, []);

  const user = mounted ? getCurrentUser() : null;

  return (
    <div className="flex min-h-screen w-full bg-background text-foreground font-sans selection:bg-primary selection:text-white transition-colors duration-200">
      {/* Fixed Left Sidebar */}
      <AppSidebar
        role={user?.role || "claimant"}
        userName={user?.name || "Claimant"}
        userEmail={user?.email || "claimant@example.com"}
      />

      {/* Main Content Area */}
      <div className="flex min-w-0 flex-1 flex-col overflow-x-hidden">
        <AppHeader
          userName={user?.name || "Claimant"}
          userRole={user?.role || "claimant"}
          {...(title === undefined ? {} : { title })}
          {...(breadcrumbs === undefined ? {} : { breadcrumbs })}
        />
        <main className="flex-1 p-6 lg:p-8">
          <div className="mx-auto max-w-[1600px]">{children}</div>
        </main>
      </div>
    </div>
  );
}
