import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { LandingPortal } from "@/components/landing/LandingPortal";
import { getCurrentUser } from "@/api/auth";

export const Route = createFileRoute("/auth")({
  head: () => ({
    meta: [
      { title: "ClaimBridge — Secure Portal Access & Entrance" },
      {
        name: "description",
        content:
          "Autonomous Medical Claim Intelligence powered by multi-document OCR, RAG Policy Verification, and Readiness Engines.",
      },
    ],
  }),
  component: AuthPage,
});

function AuthPage() {
  const navigate = useNavigate();

  const handleAuthenticated = () => {
    const user = getCurrentUser();
    if (user?.role === "claimant") {
      navigate({ to: "/claims" });
    } else {
      navigate({ to: "/" });
    }
  };

  return <LandingPortal onAuthenticated={handleAuthenticated} />;
}