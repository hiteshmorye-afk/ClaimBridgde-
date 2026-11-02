import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ShieldCheck,
  Building2,
  FileCheck2,
  ArrowRight,
  Activity,
  CheckCircle2,
  Sparkles,
  Sun,
  Moon,
  UserPlus,
  AlertCircle,
  Check,
  X,
  Lock,
  Mail,
  Key,
  ArrowLeft,
  RefreshCw,
  KeyRound,
} from "lucide-react";
import {
  loginUser,
  registerUser,
  registerTpaApplicant,
  registerInvited,
  verifyEmailOtp,
  resendEmailOtp,
  forgotPassword,
  resetPassword,
  logoutUser,
} from "@/api/auth";
import { useTheme } from "@/hooks/useTheme";
import { toast } from "sonner";

interface LandingPortalProps {
  onAuthenticated: () => void;
}

type AuthMode = "signin" | "signup" | "forgot" | "reset";
type PortalSelection = "TPA" | "Claimant";

export function LandingPortal({ onAuthenticated }: LandingPortalProps) {
  const { theme, toggleTheme, isDark } = useTheme();

  // Splash screen transition
  const [showSplash, setShowSplash] = useState(true);

  // Authentication Area: TWO Distinct Portals
  // 1. TPA LOGIN (Claims Officer & TPA Reviewers)
  // 2. USER LOGIN (User, Patient & Hospital Coordinators)
  const [portalType, setPortalType] = useState<PortalSelection>("Claimant");

  // Form Mode: signin, signup, forgot password, reset password
  const [authMode, setAuthMode] = useState<AuthMode>("signin");

  // Form fields
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [fullName, setFullName] = useState("");
  const [phone, setPhone] = useState("");
  const [organization, setOrganization] = useState("");
  const [invitationToken, setInvitationToken] = useState("");

  // OTP Verification & Password Reset
  const [pendingChallenge, setPendingChallenge] = useState<string | null>(null);
  const [resetChallengeId, setResetChallengeId] = useState<string | null>(null);
  const [otpCode, setOtpCode] = useState("");
  const [activationMessage, setActivationMessage] = useState("");

  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const [rateLimitUntil, setRateLimitUntil] = useState<number | null>(null);
  const [rateLimitSecondsLeft, setRateLimitSecondsLeft] = useState(0);
  const [touched, setTouched] = useState<Record<string, boolean>>({});

  // Auto-dismiss splash screen
  useEffect(() => {
    const timer = setTimeout(() => {
      setShowSplash(false);
    }, 2000);
    return () => clearTimeout(timer);
  }, []);

  useEffect(() => {
    if (!rateLimitUntil) {
      setRateLimitSecondsLeft(0);
      return;
    }

    const updateCountdown = () => {
      const remaining = Math.max(0, Math.ceil((rateLimitUntil - Date.now()) / 1000));
      setRateLimitSecondsLeft(remaining);
      if (remaining <= 0) {
        setRateLimitUntil(null);
      }
    };

    updateCountdown();
    const timer = window.setInterval(updateCountdown, 1000);
    return () => window.clearInterval(timer);
  }, [rateLimitUntil]);

  // Validation rules
  const isValidIdentifier = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());
  const isMinLength = password.length >= 12;
  const hasUpper = /[A-Z]/.test(password);
  const hasLower = /[a-z]/.test(password);
  const hasSpecialOrNum = /[!@#$%^&*(),.?":{}|<>0-9]/.test(password);
  const isStrongPassword = isMinLength && hasUpper && hasLower && hasSpecialOrNum;
  const isPasswordMatch =
    authMode === "signup" || authMode === "reset"
      ? password.length > 0 && password === confirmPassword
      : true;

  // Password strength score (0 to 4)
  const strengthScore = [isMinLength, hasUpper, hasLower, hasSpecialOrNum].filter(
    Boolean
  ).length;

  const handleBlur = (field: string) => {
    setTouched((prev) => ({ ...prev, [field]: true }));
  };

  // Demo Autofill for convenient testing
  const handleDemoAutofill = () => {
    if (portalType === "TPA") {
      setEmail("claims_officer.demo@claimbridge.test");
      setPassword("SecurePass#2026");
      if (authMode === "signup") {
        setFullName("Dr. Arvind Sharma");
        setOrganization("MediAssist TPA Healthcare");
        setPhone("+919876543210");
        setConfirmPassword("SecurePass#2026");
      }
      toast.info("TPA test credentials filled. Register a real account if no seeded user exists in this environment.");
    } else {
      setEmail("claimant.demo@claimbridge.test");
      setPassword("SecurePass#2026");
      if (authMode === "signup") {
        setFullName("Rajesh Kumar");
        setPhone("+919812345678");
        setConfirmPassword("SecurePass#2026");
      }
      toast.info("Claimant test credentials filled. Register a real account if no seeded user exists in this environment.");
    }
  };

  // Sign In Handler with Strict Backend-Verified Role Authentication
  const handleSignIn = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!isValidIdentifier) {
      toast.error("Please enter a valid work or personal email address.");
      return;
    }
    if (password.length < 6) {
      toast.error("Password must be at least 6 characters.");
      return;
    }

    setIsAuthenticating(true);

    try {
      const user = await loginUser({ email, password });

      // Determine the canonical operational role from the authenticated account
      const canonicalRole = (
        user.canonical_role ||
        user.role ||
        ""
      ).toLowerCase();

      // STRICT ROLE ENFORCEMENT AGAINST PORTAL SELECTION
      if (portalType === "TPA") {
        // TPA LOGIN must authenticate against claim_officer (or admin)
        const isClaimOfficer = [
          "claim_officer",
          "claims_officer",
          "tpa_reviewer",
          "reviewer",
          "admin",
        ].includes(canonicalRole);

        if (!isClaimOfficer) {
          await logoutUser();
          setIsAuthenticating(false);
          toast.error(
            "Access denied for TPA Login: This account is registered as a User / Claimant. Please select USER LOGIN to sign in."
          );
          return;
        }
      } else {
        // USER LOGIN must authenticate against claimant (or admin)
        const isClaimant = [
          "claimant",
          "hospital_coordinator",
          "patient",
          "coordinator",
          "admin",
        ].includes(canonicalRole);

        if (!isClaimant) {
          await logoutUser();
          setIsAuthenticating(false);
          toast.error(
            "Access denied for User Login: This account is registered as a Claim Officer / TPA. Please select TPA LOGIN to sign in."
          );
          return;
        }
      }

      setIsAuthenticating(false);
      onAuthenticated();
      toast.success(`Welcome back, ${user.name || user.email}!`);
    } catch (err: any) {
      setIsAuthenticating(false);
      toast.error(err.message || "Authentication failed. Please verify credentials.");
    }
  };

  // Forgot Password: Request OTP challenge
  const handleForgotPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!isValidIdentifier) {
      toast.error("Please enter a valid registered email address.");
      return;
    }

    setIsAuthenticating(true);
    try {
      const res = await forgotPassword(email);
      setResetChallengeId(res.challenge_id);
      setAuthMode("reset");
      setOtpCode("");
      toast.success("Verification code sent! Please check your email inbox.");
    } catch (err: any) {
      toast.error(err.message || "Failed to initiate password reset.");
    } finally {
      setIsAuthenticating(false);
    }
  };

  // Reset Password: Submit OTP + New Password
  const handleResetPassword = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!resetChallengeId) {
      toast.error("No active password reset session. Please request a new code.");
      setAuthMode("forgot");
      return;
    }
    if (!/^\d{6}$/.test(otpCode)) {
      toast.error("Enter the valid 6-digit verification code.");
      return;
    }
    if (!isStrongPassword) {
      toast.error(
        "New password must be at least 12 characters and include uppercase, lowercase, and a number or symbol."
      );
      return;
    }
    if (!isPasswordMatch) {
      toast.error("Passwords do not match. Please verify.");
      return;
    }

    setIsAuthenticating(true);
    try {
      await resetPassword({
        challenge_id: resetChallengeId,
        otp_code: otpCode,
        new_password: password,
      });
      toast.success("Password reset successfully! You may now sign in.");
      setAuthMode("signin");
      setPassword("");
      setConfirmPassword("");
      setOtpCode("");
      setResetChallengeId(null);
    } catch (err: any) {
      toast.error(err.message || "Password reset failed. Invalid or expired code.");
    } finally {
      setIsAuthenticating(false);
    }
  };

  // Create Account Handler
  const handleSignUp = async (e: React.FormEvent) => {
    e.preventDefault();

    setTouched({
      fullName: true,
      email: true,
      phone: true,
      password: true,
      confirmPassword: true,
      organization: true,
    });

    if (!fullName.trim()) {
      toast.error("Full Name is required.");
      return;
    }
    if (!isValidIdentifier) {
      toast.error("Enter a valid email address.");
      return;
    }
    if (!/^\+?[0-9]{8,15}$/.test(phone.trim())) {
      toast.error("Enter a valid phone number with 8 to 15 digits.");
      return;
    }
    if (portalType === "TPA" && !invitationToken.trim() && !organization.trim()) {
      toast.error("TPA organization name is required for provisioning.");
      return;
    }
    if (!isStrongPassword) {
      toast.error(
        "Password must be at least 12 characters and include uppercase, lowercase, and a number or symbol."
      );
      return;
    }
    if (!isPasswordMatch) {
      toast.error("Passwords do not match. Please verify.");
      return;
    }

    setIsAuthenticating(true);

    try {
      if (portalType === "TPA" && invitationToken.trim()) {
        // Direct invited TPA employee onboarding
        await registerInvited({
          invitation_token: invitationToken.trim(),
          fullName: fullName.trim(),
          phone: phone.trim(),
          password,
        });
        toast.success("Invited employee account activated successfully!");
        setTimeout(() => {
          setIsAuthenticating(false);
          onAuthenticated();
        }, 500);
        return;
      }

      if (portalType === "TPA") {
        const res = await registerTpaApplicant({
          fullName,
          phone,
          email,
          password,
          organization,
        });
        setPendingChallenge(res.challenge_id);
        if (res.demo_mode) {
          setActivationMessage(
            res.demo_hint || "Development demo mode: Check the backend console for your verification code."
          );
          toast.warning(
            res.message || "Development demo mode: Check the backend console for your verification code."
          );
        } else {
          setActivationMessage("");
          toast.success(
            res.message || "Verification code sent successfully to your registered email address."
          );
        }
      } else {
        const res = await registerUser({
          fullName,
          phone,
          email,
          password,
          role: "claimant",
        });
        setPendingChallenge(res.challenge_id);
        if (res.demo_mode) {
          setActivationMessage(
            res.demo_hint || "Development demo mode: Check the backend console for your verification code."
          );
          toast.warning(
            res.message || "Development demo mode: Check the backend console for your verification code."
          );
        } else {
          setActivationMessage("");
          toast.success(
            res.message || "Verification code sent successfully to your registered email address."
          );
        }
      }
    } catch (err: any) {
      const retryAfter = typeof err?.retryAfter === "number" ? err.retryAfter : undefined;
      if (retryAfter) {
        setRateLimitUntil(Date.now() + retryAfter * 1000);
        toast.error(`Too many verification requests. Please wait ${retryAfter} seconds before trying again.`);
      } else {
        toast.error(err.message || "Account registration failed.");
      }
    } finally {
      setIsAuthenticating(false);
    }
  };

  // OTP Verification Submission
  const handleVerifyOtp = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!pendingChallenge) return;

    if (!/^\d{6}$/.test(otpCode)) {
      toast.error("Enter the six-digit verification code.");
      return;
    }

    setIsAuthenticating(true);
    try {
      const user = await verifyEmailOtp(pendingChallenge, otpCode);
      setPendingChallenge(null);
      setOtpCode("");

      if (user) {
        toast.success("Email verified! Your account is active.");
        setTimeout(() => {
          setIsAuthenticating(false);
          onAuthenticated();
        }, 500);
      } else {
        const message = "Email verified successfully. Your TPA organization is awaiting authorization.";
        setActivationMessage(message);
        toast.info(message);
        setIsAuthenticating(false);
      }
    } catch (err: any) {
      setIsAuthenticating(false);
      toast.error(err.message || "Email verification failed. Invalid or expired code.");
    }
  };

  const providerLogos = ["HCG", "Apollo Hospitals", "MAX Healthcare", "Fortis", "Manipal Hospitals"];

  return (
    <div className="relative min-h-screen w-full bg-slate-100 dark:bg-[#080C14] text-slate-900 dark:text-[#F9FAFB] overflow-x-hidden font-sans transition-colors duration-300">
      
      {/* Intro Splash Animation */}
      <AnimatePresence>
        {showSplash && (
          <motion.div
            initial={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.6 }}
            className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-[#080C14] text-white"
          >
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ duration: 0.5, ease: "easeOut" }}
              className="flex size-20 items-center justify-center rounded-2xl bg-gradient-to-br from-[#3B82F6] to-[#06B6D4] shadow-2xl shadow-[#3B82F6]/40"
            >
              <ShieldCheck className="size-12 text-white" />
            </motion.div>
            <motion.h1
              initial={{ y: 20, opacity: 0 }}
              animate={{ y: 0, opacity: 1 }}
              transition={{ delay: 0.3, duration: 0.5 }}
              className="mt-6 text-3xl font-extrabold tracking-tight"
            >
              Claim<span className="text-[#3B82F6]">Bridge</span>
            </motion.h1>
            <motion.p
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              transition={{ delay: 0.5, duration: 0.5 }}
              className="mt-2 text-xs font-mono uppercase tracking-widest text-[#06B6D4]"
            >
              Initializing AI Claim Engine...
            </motion.p>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Background Ambient Glow */}
      <div className="absolute top-0 left-1/4 size-[700px] rounded-full bg-[#3B82F6]/10 blur-[150px] pointer-events-none" />
      <div className="absolute bottom-0 left-0 size-[500px] rounded-full bg-[#06B6D4]/10 blur-[150px] pointer-events-none" />

      {/* Top Header Navigation */}
      <header className="relative z-30 flex items-center justify-between px-6 py-4 lg:px-12 border-b border-slate-200/80 dark:border-[#1F2937]/80 bg-white/70 dark:bg-[#0B0F17]/70 backdrop-blur-md">
        <div className="flex items-center gap-3">
          <div className="flex size-10 items-center justify-center rounded-xl bg-gradient-to-br from-[#3B82F6] to-[#06B6D4] shadow-md shadow-[#3B82F6]/30">
            <ShieldCheck className="size-6 text-white" />
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="text-xl font-bold tracking-tight text-slate-900 dark:text-white">
                Claim<span className="text-[#3B82F6]">Bridge</span>
              </span>
              <span className="rounded-full bg-[#06B6D4]/10 border border-[#06B6D4]/30 px-2 py-0.5 font-mono text-[10px] text-[#06B6D4]">
                Insurance Intelligence
              </span>
            </div>
            <p className="text-[11px] text-slate-500 dark:text-[#9CA3AF] hidden sm:block">
              Verify, validate & prepare insurance claims before submission
            </p>
          </div>
        </div>

        {/* Header Right Actions */}
        <div className="flex items-center gap-4">
          <button
            type="button"
            onClick={handleDemoAutofill}
            className="hidden sm:inline-flex items-center gap-1.5 rounded-xl border border-[#3B82F6]/30 bg-[#3B82F6]/10 px-3 py-1.5 text-xs font-semibold text-[#3B82F6] hover:bg-[#3B82F6]/20 transition"
          >
            <Sparkles className="size-3.5" /> Demo Autofill
          </button>

          <div className="hidden md:flex items-center gap-2 rounded-full border border-emerald-500/30 bg-emerald-500/10 px-3 py-1 text-xs font-mono text-emerald-600 dark:text-emerald-400">
            <span className="size-2 rounded-full bg-emerald-500 animate-ping" />
            <span>System operational</span>
          </div>

          <button
            type="button"
            onClick={toggleTheme}
            className="flex size-10 items-center justify-center rounded-xl border border-slate-200 dark:border-[#1F2937] bg-slate-50 dark:bg-[#0B0F17] text-slate-600 dark:text-slate-300 hover:text-[#3B82F6] transition"
            aria-label="Toggle theme"
          >
            {isDark ? <Sun className="size-4" /> : <Moon className="size-4" />}
          </button>
        </div>
      </header>

      {/* Main Hero Container */}
      <main className="relative z-20 mx-auto max-w-7xl px-6 py-8 lg:px-12 lg:py-12">
        <div className="grid gap-12 lg:grid-cols-12 lg:items-start">
          
          {/* ========================================================================= */}
          {/* LEFT HERO: HEADLINE + PROMINENT MEDICAL VISUAL SHOWCASE */}
          {/* ========================================================================= */}
          <div className="lg:col-span-7 space-y-8">
            
            {/* Headline Badge & Title */}
            <div className="space-y-4">
              <div className="inline-flex items-center gap-2 rounded-full border border-[#06B6D4]/30 bg-[#06B6D4]/10 px-3 py-1 text-xs font-semibold text-[#06B6D4]">
                <Sparkles className="size-3.5" />
                AI-POWERED CLAIM INTELLIGENCE
              </div>

              <h1 className="text-4xl font-extrabold tracking-tight text-slate-900 dark:text-white sm:text-5xl lg:text-6xl leading-[1.1]">
                From documents to <br />
                <span className="bg-gradient-to-r from-[#3B82F6] via-[#06B6D4] to-[#10B981] bg-clip-text text-transparent">
                  decisions.
                </span>
              </h1>

              <p className="max-w-2xl text-base text-slate-600 dark:text-[#9CA3AF] leading-relaxed sm:text-lg">
                Autonomous Medical Claim Intelligence powered by multi-document OCR, RAG Policy Verification, and Readiness Engines.
              </p>
            </div>

            {/* PROMINENT HIGH-DEFINITION MEDICAL VISUAL HERO CARD */}
            <div className="relative overflow-hidden rounded-3xl border border-slate-300 dark:border-[#1F2937] bg-white dark:bg-[#0E1420] shadow-2xl p-6 lg:p-8">
              
              {/* Background Medical Hospital Image */}
              <div
                className="absolute inset-0 bg-cover bg-center transition-all duration-500 opacity-20 dark:opacity-40 mix-blend-luminosity dark:mix-blend-overlay"
                style={{
                  backgroundImage: isDark
                    ? "url('https://images.unsplash.com/photo-1519494026892-80bbd2d6fd0d?auto=format&fit=crop&w=1600&q=80')"
                    : "url('https://images.unsplash.com/photo-1551076805-e1869033e561?auto=format&fit=crop&w=1600&q=80')",
                }}
              />

              {/* Content Overlay */}
              <div className="relative z-10 flex min-h-[300px] flex-col justify-between">
                
                {/* Top Overlay Badge */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2 rounded-full border border-slate-200 dark:border-[#1F2937] bg-white/80 dark:bg-[#111827]/80 px-3 py-1 text-xs font-mono backdrop-blur-md shadow-sm">
                    <span className="size-2 rounded-full bg-[#3B82F6] animate-ping" />
                    <span className="text-slate-800 dark:text-white font-semibold">Live Pipeline Stream</span>
                  </div>
                  <span className="text-xs font-mono text-[#06B6D4]">CLAIMBRIDGE-AI</span>
                </div>

                {/* Animated ECG Pulse Wave Graph */}
                <div className="my-6 relative flex items-center justify-center">
                  <svg className="w-full h-24 stroke-[#06B6D4] fill-none stroke-2 opacity-80" viewBox="0 0 500 100">
                    <motion.path
                      d="M 0,50 L 100,50 L 120,20 L 140,80 L 160,10 L 180,90 L 200,50 L 300,50 L 320,30 L 340,70 L 360,50 L 500,50"
                      initial={{ pathLength: 0 }}
                      animate={{ pathLength: 1 }}
                      transition={{ repeat: Infinity, duration: 3, ease: "linear" }}
                    />
                  </svg>
                </div>

              </div>

            </div>

          </div>

          {/* ========================================================================= */}
          {/* RIGHT COLUMN: RESTORED AUTHENTICATION AREA WITH TWO DISTINCT PORTALS */}
          {/* ========================================================================= */}
          <div className="lg:col-span-5">
            <div className="relative rounded-3xl border border-slate-300 dark:border-[#1F2937] bg-white/95 dark:bg-[#0E1420]/95 p-6 shadow-2xl backdrop-blur-xl sm:p-8 space-y-6">
              
              {/* Form Title & Subtitle */}
              <div>
                <h2 className="text-2xl font-bold tracking-tight text-slate-900 dark:text-white">
                  {pendingChallenge
                    ? "Verify Your Email"
                    : authMode === "signin"
                    ? "Welcome to ClaimBridge"
                    : authMode === "signup"
                    ? "Create ClaimBridge Account"
                    : authMode === "forgot"
                    ? "Forgot Password"
                    : "Reset Your Password"}
                </h2>
                <p className="mt-1 text-xs text-slate-500 dark:text-[#9CA3AF]">
                  {pendingChallenge
                    ? `Enter the 6-digit verification code sent to ${email}.`
                    : authMode === "signin"
                    ? "Select your portal option and sign in with your verified credentials."
                    : authMode === "signup"
                    ? "Enter your details to create your enterprise healthcare account."
                    : authMode === "forgot"
                    ? "Enter your registered email address to receive a 6-digit reset code."
                    : "Enter the 6-digit code and choose a strong new password."}
                </p>
              </div>

              {/* TWO DISTINCT PORTAL SELECTION CARDS (TPA LOGIN vs USER LOGIN) */}
              {!pendingChallenge && authMode !== "forgot" && authMode !== "reset" && (
                <div className="grid grid-cols-2 gap-3">
                  
                  {/* Card 1: TPA LOGIN */}
                  <button
                    type="button"
                    onClick={() => {
                      setPortalType("TPA");
                      setTouched({});
                    }}
                    className={`flex flex-col justify-between p-4 rounded-2xl border text-left transition-all ${
                      portalType === "TPA"
                        ? "border-[#06B6D4] bg-[#06B6D4]/10 shadow-lg shadow-[#06B6D4]/20"
                        : "border-slate-200 dark:border-[#1F2937] bg-slate-50 dark:bg-[#0B0F17] hover:border-slate-300"
                    }`}
                  >
                    <div className="flex size-9 items-center justify-center rounded-xl bg-[#06B6D4]/20 text-[#06B6D4]">
                      <Activity className="size-5" />
                    </div>
                    <div className="mt-3">
                      <p className="text-xs font-bold text-slate-900 dark:text-white">TPA LOGIN</p>
                      <p className="mt-0.5 text-[10px] text-slate-500 dark:text-[#9CA3AF]">
                        Claims Officer & TPA Reviewer Portal
                      </p>
                    </div>
                  </button>

                  {/* Card 2: USER LOGIN */}
                  <button
                    type="button"
                    onClick={() => {
                      setPortalType("Claimant");
                      setTouched({});
                    }}
                    className={`flex flex-col justify-between p-4 rounded-2xl border text-left transition-all ${
                      portalType === "Claimant"
                        ? "border-[#3B82F6] bg-[#3B82F6]/10 shadow-lg shadow-[#3B82F6]/20"
                        : "border-slate-200 dark:border-[#1F2937] bg-slate-50 dark:bg-[#0B0F17] hover:border-slate-300"
                    }`}
                  >
                    <div className="flex size-9 items-center justify-center rounded-xl bg-[#3B82F6]/20 text-[#3B82F6]">
                      <Building2 className="size-5" />
                    </div>
                    <div className="mt-3">
                      <p className="text-xs font-bold text-slate-900 dark:text-white">USER LOGIN</p>
                      <p className="mt-0.5 text-[10px] text-slate-500 dark:text-[#9CA3AF]">
                        User, Patient & Hospital Portal
                      </p>
                    </div>
                  </button>

                </div>
              )}

              {/* =================================================================== */}
              {/* OTP EMAIL VERIFICATION FORM */}
              {/* =================================================================== */}
              {pendingChallenge ? (
                <form onSubmit={handleVerifyOtp} className="space-y-4">
                  <div className="space-y-2">
                    <label className="text-xs font-semibold text-slate-600 dark:text-[#9CA3AF]">
                      6-Digit Verification Code
                    </label>
                    <input
                      type="text"
                      inputMode="numeric"
                      autoComplete="one-time-code"
                      pattern="[0-9]{6}"
                      maxLength={6}
                      value={otpCode}
                      onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, ""))}
                      required
                      placeholder="123456"
                      className="h-12 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 text-center font-mono text-xl tracking-[0.5em] text-slate-900 outline-none focus:border-[#3B82F6] dark:border-[#1F2937] dark:bg-[#0B0F17] dark:text-white"
                    />
                  </div>

                  {activationMessage && (
                    <p className="rounded-xl bg-amber-500/10 p-3 text-xs text-amber-700 dark:text-amber-300">
                      {activationMessage}
                    </p>
                  )}

                  <button
                    type="submit"
                    disabled={isAuthenticating || otpCode.length !== 6}
                    className="flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-[#3B82F6] to-[#06B6D4] font-bold text-white shadow-lg shadow-[#3B82F6]/30 hover:shadow-xl transition disabled:opacity-60"
                  >
                    {isAuthenticating ? "Verifying..." : "Verify & Activate Account"}
                  </button>

                  <div className="flex items-center justify-between pt-2 text-xs">
                    <button
                      type="button"
                      onClick={async () => {
                        if (rateLimitSecondsLeft > 0 || isAuthenticating) return;
                        try {
                          await resendEmailOtp(email);
                          toast.success("Verification code resent to your email.");
                        } catch (err: any) {
                          const retryAfter = typeof err?.retryAfter === "number" ? err.retryAfter : undefined;
                          if (retryAfter) {
                            setRateLimitUntil(Date.now() + retryAfter * 1000);
                            toast.error(`Too many verification requests. Please wait ${retryAfter} seconds before trying again.`);
                          } else {
                            toast.error(err.message || "Could not resend code.");
                          }
                        }
                      }}
                      className="text-[#3B82F6] hover:underline disabled:opacity-50 disabled:cursor-not-allowed"
                      disabled={rateLimitSecondsLeft > 0 || isAuthenticating}
                    >
                      {rateLimitSecondsLeft > 0 ? `Resend code (${rateLimitSecondsLeft}s)` : "Resend code"}
                    </button>
                    <button
                      type="button"
                      onClick={() => {
                        setPendingChallenge(null);
                        setAuthMode("signin");
                      }}
                      className="text-slate-500 hover:underline"
                    >
                      Cancel
                    </button>
                  </div>
                </form>
              ) : authMode === "forgot" ? (
                /* ================================================================= */
                /* FORGOT PASSWORD FORM */
                /* ================================================================= */
                <form onSubmit={handleForgotPassword} className="space-y-4">
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-slate-600 dark:text-[#9CA3AF]">
                      Registered Email Address <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="email"
                      required
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      placeholder="name@example.com"
                      className="h-11 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 text-sm text-slate-900 outline-none focus:border-[#3B82F6] dark:border-[#1F2937] dark:bg-[#0B0F17] dark:text-white"
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={isAuthenticating}
                    className="flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-[#3B82F6] to-[#06B6D4] font-bold text-white shadow-lg shadow-[#3B82F6]/30 hover:shadow-xl transition disabled:opacity-60"
                  >
                    {isAuthenticating ? "Sending Code..." : "Send Verification Code"}
                  </button>

                  <div className="pt-2 text-center">
                    <button
                      type="button"
                      onClick={() => setAuthMode("signin")}
                      className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#3B82F6] hover:underline"
                    >
                      <ArrowLeft className="size-3.5" /> Back to Sign In
                    </button>
                  </div>
                </form>
              ) : authMode === "reset" ? (
                /* ================================================================= */
                /* RESET PASSWORD FORM */
                /* ================================================================= */
                <form onSubmit={handleResetPassword} className="space-y-4">
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-slate-600 dark:text-[#9CA3AF]">
                      6-Digit Reset Code <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="text"
                      inputMode="numeric"
                      pattern="[0-9]{6}"
                      maxLength={6}
                      required
                      value={otpCode}
                      onChange={(e) => setOtpCode(e.target.value.replace(/\D/g, ""))}
                      placeholder="123456"
                      className="h-11 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 text-center font-mono text-lg tracking-[0.4em] text-slate-900 outline-none focus:border-[#3B82F6] dark:border-[#1F2937] dark:bg-[#0B0F17] dark:text-white"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-slate-600 dark:text-[#9CA3AF]">
                      New Password (12+ characters) <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="password"
                      required
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      placeholder="Enter new strong password"
                      className="h-11 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 text-sm text-slate-900 outline-none focus:border-[#3B82F6] dark:border-[#1F2937] dark:bg-[#0B0F17] dark:text-white"
                    />
                  </div>

                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-slate-600 dark:text-[#9CA3AF]">
                      Confirm New Password <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="password"
                      required
                      value={confirmPassword}
                      onChange={(e) => setConfirmPassword(e.target.value)}
                      placeholder="Confirm new password"
                      className="h-11 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 text-sm text-slate-900 outline-none focus:border-[#3B82F6] dark:border-[#1F2937] dark:bg-[#0B0F17] dark:text-white"
                    />
                  </div>

                  <button
                    type="submit"
                    disabled={isAuthenticating}
                    className="flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-[#3B82F6] to-[#06B6D4] font-bold text-white shadow-lg shadow-[#3B82F6]/30 hover:shadow-xl transition disabled:opacity-60"
                  >
                    {isAuthenticating ? "Updating..." : "Reset Password & Sign In"}
                  </button>

                  <div className="pt-2 text-center">
                    <button
                      type="button"
                      onClick={() => setAuthMode("signin")}
                      className="inline-flex items-center gap-1.5 text-xs font-semibold text-[#3B82F6] hover:underline"
                    >
                      <ArrowLeft className="size-3.5" /> Back to Sign In
                    </button>
                  </div>
                </form>
              ) : (
                /* ================================================================= */
                /* SIGN IN & CREATE ACCOUNT FORMS */
                /* ================================================================= */
                <form
                  onSubmit={authMode === "signin" ? handleSignIn : handleSignUp}
                  className="space-y-4"
                >
                  {/* SIGN UP EXTRA FIELDS */}
                  {authMode === "signup" && (
                    <>
                      <div className="space-y-1.5">
                        <label className="text-xs font-semibold text-slate-600 dark:text-[#9CA3AF]">
                          Full Name <span className="text-red-500">*</span>
                        </label>
                        <input
                          type="text"
                          value={fullName}
                          onChange={(e) => setFullName(e.target.value)}
                          onBlur={() => handleBlur("fullName")}
                          required
                          className={`h-11 w-full rounded-xl border px-4 text-sm text-slate-900 dark:text-white bg-slate-50 dark:bg-[#0B0F17] outline-none transition ${
                            touched["fullName"] && !fullName.trim()
                              ? "border-red-500 focus:border-red-500"
                              : "border-slate-200 dark:border-[#1F2937] focus:border-[#3B82F6]"
                          }`}
                          placeholder="Your full name"
                        />
                      </div>

                      <div className="space-y-1.5">
                        <label className="text-xs font-semibold text-slate-600 dark:text-[#9CA3AF]">
                          Phone Number <span className="text-red-500">*</span>
                        </label>
                        <input
                          type="tel"
                          value={phone}
                          onChange={(e) => setPhone(e.target.value)}
                          required
                          placeholder="+919876543210"
                          className="h-11 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 text-sm text-slate-900 outline-none focus:border-[#3B82F6] dark:border-[#1F2937] dark:bg-[#0B0F17] dark:text-white"
                        />
                      </div>

                      {portalType === "TPA" && (
                        <>
                          <div className="space-y-1.5">
                            <label className="text-xs font-semibold text-slate-600 dark:text-[#9CA3AF]">
                              TPA Organization <span className="text-red-500">*</span>
                            </label>
                            <input
                              type="text"
                              value={organization}
                              onChange={(e) => setOrganization(e.target.value)}
                              placeholder="e.g. MediAssist TPA Services"
                              className="h-11 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 text-sm text-slate-900 outline-none focus:border-[#3B82F6] dark:border-[#1F2937] dark:bg-[#0B0F17] dark:text-white"
                            />
                          </div>

                          <div className="space-y-1.5">
                            <label className="text-xs font-semibold text-slate-600 dark:text-[#9CA3AF]">
                              Invitation Token (Optional)
                            </label>
                            <input
                              type="text"
                              value={invitationToken}
                              onChange={(e) => setInvitationToken(e.target.value)}
                              placeholder="Paste employee onboarding invitation token"
                              className="h-11 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 text-xs font-mono text-slate-900 outline-none focus:border-[#3B82F6] dark:border-[#1F2937] dark:bg-[#0B0F17] dark:text-white"
                            />
                          </div>
                        </>
                      )}
                    </>
                  )}

                  {/* EMAIL ADDRESS FIELD */}
                  <div className="space-y-1.5">
                    <label className="text-xs font-semibold text-slate-600 dark:text-[#9CA3AF]">
                      {portalType === "TPA" ? "TPA Official Email" : "Email Address"}{" "}
                      <span className="text-red-500">*</span>
                    </label>
                    <input
                      type="email"
                      value={email}
                      onChange={(e) => setEmail(e.target.value)}
                      onBlur={() => handleBlur("email")}
                      required
                      placeholder={
                        portalType === "TPA"
                          ? "officer@tpa-services.com"
                          : "claimant@example.com"
                      }
                      className={`h-11 w-full rounded-xl border px-4 text-sm text-slate-900 dark:text-white bg-slate-50 dark:bg-[#0B0F17] outline-none transition ${
                        touched["email"] && !isValidIdentifier
                          ? "border-red-500 focus:border-red-500"
                          : "border-slate-200 dark:border-[#1F2937] focus:border-[#3B82F6]"
                      }`}
                    />
                  </div>

                  {/* PASSWORD FIELD WITH FORGOT PASSWORD OPTION */}
                  <div className="space-y-1.5">
                    <div className="flex justify-between items-center text-xs">
                      <label className="font-semibold text-slate-600 dark:text-[#9CA3AF]">
                        Password <span className="text-red-500">*</span>
                      </label>
                      {authMode === "signin" && (
                        <button
                          type="button"
                          onClick={() => {
                            setAuthMode("forgot");
                            setTouched({});
                          }}
                          className="font-medium text-[#3B82F6] hover:underline"
                        >
                          Forgot password?
                        </button>
                      )}
                    </div>
                    <input
                      type="password"
                      value={password}
                      onChange={(e) => setPassword(e.target.value)}
                      onBlur={() => handleBlur("password")}
                      required
                      placeholder="Enter strong password"
                      className={`h-11 w-full rounded-xl border px-4 text-sm text-slate-900 dark:text-white bg-slate-50 dark:bg-[#0B0F17] outline-none transition ${
                        touched["password"] && authMode === "signup" && !isStrongPassword
                          ? "border-amber-500 focus:border-amber-500"
                          : "border-slate-200 dark:border-[#1F2937] focus:border-[#3B82F6]"
                      }`}
                    />

                    {/* LIVE PASSWORD STRENGTH METER (FOR SIGNUP) */}
                    {authMode === "signup" && password.length > 0 && (
                      <div className="mt-2 space-y-2 rounded-xl border border-slate-200 dark:border-[#1F2937] bg-slate-50 dark:bg-[#0B0F17] p-3 text-xs">
                        <div className="flex items-center justify-between">
                          <span className="text-[11px] text-slate-500 dark:text-[#9CA3AF]">
                            Password Strength:
                          </span>
                          <span
                            className={`font-mono font-bold text-[11px] ${
                              strengthScore <= 2
                                ? "text-red-500"
                                : strengthScore === 3
                                ? "text-amber-500"
                                : "text-emerald-500"
                            }`}
                          >
                            {strengthScore <= 2
                              ? "Weak"
                              : strengthScore === 3
                              ? "Medium"
                              : "Strong & Valid"}
                          </span>
                        </div>

                        <div className="h-1.5 w-full bg-slate-200 dark:bg-[#1F2937] rounded-full overflow-hidden">
                          <div
                            className={`h-full transition-all duration-300 ${
                              strengthScore <= 2
                                ? "w-1/4 bg-red-500"
                                : strengthScore === 3
                                ? "w-3/4 bg-amber-500"
                                : "w-full bg-emerald-500"
                            }`}
                          />
                        </div>

                        <div className="grid grid-cols-2 gap-1.5 pt-1 text-[10px]">
                          <span
                            className={`flex items-center gap-1 ${
                              isMinLength
                                ? "text-emerald-500 font-semibold"
                                : "text-slate-400"
                            }`}
                          >
                            {isMinLength ? <Check className="size-3" /> : <X className="size-3" />}{" "}
                            12+ Characters
                          </span>
                          <span
                            className={`flex items-center gap-1 ${
                              hasUpper
                                ? "text-emerald-500 font-semibold"
                                : "text-slate-400"
                            }`}
                          >
                            {hasUpper ? <Check className="size-3" /> : <X className="size-3" />}{" "}
                            Uppercase (A-Z)
                          </span>
                          <span
                            className={`flex items-center gap-1 ${
                              hasLower
                                ? "text-emerald-500 font-semibold"
                                : "text-slate-400"
                            }`}
                          >
                            {hasLower ? <Check className="size-3" /> : <X className="size-3" />}{" "}
                            Lowercase (a-z)
                          </span>
                          <span
                            className={`flex items-center gap-1 ${
                              hasSpecialOrNum
                                ? "text-emerald-500 font-semibold"
                                : "text-slate-400"
                            }`}
                          >
                            {hasSpecialOrNum ? (
                              <Check className="size-3" />
                            ) : (
                              <X className="size-3" />
                            )}{" "}
                            Special / Number
                          </span>
                        </div>
                      </div>
                    )}
                  </div>

                  {/* CONFIRM PASSWORD (SIGNUP ONLY) */}
                  {authMode === "signup" && (
                    <div className="space-y-1.5">
                      <label className="text-xs font-semibold text-slate-600 dark:text-[#9CA3AF]">
                        Confirm Password <span className="text-red-500">*</span>
                      </label>
                      <input
                        type="password"
                        value={confirmPassword}
                        onChange={(e) => setConfirmPassword(e.target.value)}
                        onBlur={() => handleBlur("confirmPassword")}
                        required
                        placeholder="Re-enter password to confirm"
                        className={`h-11 w-full rounded-xl border px-4 text-sm text-slate-900 dark:text-white bg-slate-50 dark:bg-[#0B0F17] outline-none transition ${
                          touched["confirmPassword"] && !isPasswordMatch
                            ? "border-red-500 focus:border-red-500"
                            : "border-slate-200 dark:border-[#1F2937] focus:border-[#3B82F6]"
                        }`}
                      />
                    </div>
                  )}

                  {/* SUBMIT BUTTON */}
                  <button
                    type="submit"
                    disabled={isAuthenticating || rateLimitSecondsLeft > 0}
                    className="group flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-[#3B82F6] to-[#06B6D4] font-bold text-white shadow-lg shadow-[#3B82F6]/30 hover:shadow-xl transition disabled:opacity-60"
                  >
                    {isAuthenticating ? (
                      <span>Processing...</span>
                    ) : rateLimitSecondsLeft > 0 ? (
                      <span>Please wait {rateLimitSecondsLeft}s</span>
                    ) : authMode === "signin" ? (
                      <>
                        <span>Sign In as {portalType === "TPA" ? "Claim Officer" : "Claimant"}</span>
                        <ArrowRight className="size-4 transition-transform group-hover:translate-x-1" />
                      </>
                    ) : (
                      <>
                        <span>Create Account</span>
                        <UserPlus className="size-4" />
                      </>
                    )}
                  </button>
                </form>
              )}

              {/* TOGGLE BETWEEN SIGN IN & CREATE ACCOUNT */}
              {!pendingChallenge && authMode !== "forgot" && authMode !== "reset" && (
                <div className="pt-2 text-center border-t border-slate-200 dark:border-[#1F2937]">
                  {authMode === "signin" ? (
                    <p className="text-xs text-slate-600 dark:text-[#9CA3AF]">
                      Don't have a registered account?{" "}
                      <button
                        type="button"
                        onClick={() => {
                          setAuthMode("signup");
                          setTouched({});
                        }}
                        className="font-bold text-[#3B82F6] hover:underline"
                      >
                        Create Account
                      </button>
                    </p>
                  ) : (
                    <p className="text-xs text-slate-600 dark:text-[#9CA3AF]">
                      Already have an account?{" "}
                      <button
                        type="button"
                        onClick={() => {
                          setAuthMode("signin");
                          setTouched({});
                        }}
                        className="font-bold text-[#3B82F6] hover:underline"
                      >
                        Sign In
                      </button>
                    </p>
                  )}
                </div>
              )}

            </div>
          </div>

        </div>

        {/* TRUSTED PROVIDERS / HOSPITAL LOGOS FOOTER */}
        <div className="mt-12 flex flex-col items-center justify-between gap-4 border-t border-slate-200 dark:border-[#1F2937] pt-8 lg:flex-row">
          <div className="flex items-center gap-2 text-xs font-semibold text-slate-500 dark:text-[#9CA3AF]">
            <Building2 className="size-4 text-[#3B82F6]" />
            <span>Trusted by Providers. Powered by Intelligence.</span>
          </div>

          <div className="flex flex-wrap items-center justify-center gap-6 opacity-80">
            {providerLogos.map((logo) => (
              <span
                key={logo}
                className="font-display text-sm font-bold tracking-wider text-slate-700 dark:text-slate-300 hover:text-[#3B82F6] transition"
              >
                {logo}
              </span>
            ))}
            <span className="text-xs text-slate-400 dark:text-slate-600 font-mono">and more...</span>
          </div>
        </div>

      </main>
    </div>
  );
}
