import React, { useState, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  ShieldCheck,
  Building2,
  FileCheck2,
  BrainCircuit,
  Zap,
  ArrowRight,
  Activity,
  CheckCircle2,
  FileText,
  Search,
  Sparkles,
  Sun,
  Moon,
  HeartHandshake,
  UserPlus,
  AlertCircle,
  Check,
  X,
  Lock,
} from "lucide-react";
import {
  loginUser,
  registerUser,
  registerTpaApplicant,
  resendEmailOtp,
  verifyEmailOtp,
} from "@/api/auth";
import { useTheme } from "@/hooks/useTheme";
import { toast } from "sonner";

interface LandingPortalProps {
  onAuthenticated: () => void;
}

export function LandingPortal({ onAuthenticated }: LandingPortalProps) {
  const { theme, toggleTheme, isDark } = useTheme();

  // Intro splash stage vs landing cover portal
  const [showSplash, setShowSplash] = useState(true);
  const [portalType, setPortalType] = useState<"Claimant" | "TPA">("Claimant");
  
  // Auth Mode: Sign In vs Create Account
  const [authMode, setAuthMode] = useState<"signin" | "signup">("signin");

  // Dynamic Form Fields (Not hardcoded)
  const [fullName, setFullName] = useState("");
  const [organization, setOrganization] = useState("");
  const [phone, setPhone] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [pendingChallenge, setPendingChallenge] = useState<string | null>(null);
  const [otpCode, setOtpCode] = useState("");
  const [activationMessage, setActivationMessage] = useState("");
  
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const [touched, setTouched] = useState<Record<string, boolean>>({});

  // Auto-dismiss splash after sequence
  useEffect(() => {
    const timer = setTimeout(() => {
      setShowSplash(false);
    }, 2200);
    return () => clearTimeout(timer);
  }, []);

  // Validation Rules
  const isValidIdentifier = /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email.trim());
  const isMinLength = password.length >= 12;
  const hasUpper = /[A-Z]/.test(password);
  const hasLower = /[a-z]/.test(password);
  const hasSpecialOrNum = /[!@#$%^&*(),.?":{}|<>0-9]/.test(password);
  const isStrongPassword = isMinLength && hasUpper && hasLower && hasSpecialOrNum;
  const isPasswordMatch = authMode === "signup" ? password.length > 0 && password === confirmPassword : true;

  // Calculate password strength score (0 to 4)
  const strengthScore = [isMinLength, hasUpper, hasLower, hasSpecialOrNum].filter(Boolean).length;

  const handleBlur = (field: string) => {
    setTouched((prev) => ({ ...prev, [field]: true }));
  };

  const handleDemoAutofill = () => {
    setEmail("claimant.demo@claimbridge.local");
    setPassword("SecurePass#2026");
    if (authMode === "signup") {
      setFullName("Synthetic Demo Claimant");
      setOrganization("");
      setPhone("+15555550123");
      setConfirmPassword("SecurePass#2026");
    }
    toast.info("Demo fields filled. Sign-in requires a provisioned demo account.");
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    // Trigger touched state for all fields
    if (pendingChallenge) {
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
          toast.success("Email verified. Your account is active.");
          onAuthenticated();
        } else {
          const message =
            "Email verified. TPA organization authorization is still required before sign-in.";
          setActivationMessage(message);
          toast.info(message);
        }
      } catch (err: any) {
        toast.error(err.message || "Email verification failed.");
      } finally {
        setIsAuthenticating(false);
      }
      return;
    }

    setTouched({
      fullName: true,
      organization: true,
      phone: true,
      email: true,
      password: true,
      confirmPassword: true,
    });

    // Check user ID / email validation
    if (!isValidIdentifier) {
      toast.error("Please enter a valid User ID or Email address.");
      return;
    }

    // Check signup validation rules
    if (authMode === "signup") {
      if (!fullName.trim()) {
        toast.error("Full Name is required.");
        return;
      }
      if (!/^\+?[0-9]{8,15}$/.test(phone.trim())) {
        toast.error("Enter a valid phone number with 8 to 15 digits.");
        return;
      }
      if (portalType === "TPA" && !organization.trim()) {
        toast.error("TPA organization is required for the provisioning request.");
        return;
      }
      if (!isStrongPassword) {
        toast.error("Password must be at least 12 characters and include uppercase, lowercase, and a number or symbol.");
        return;
      }
      if (!isPasswordMatch) {
        toast.error("Passwords do not match. Please verify.");
        return;
      }
    } else {
      // Signin validation
      if (password.length < 6) {
        toast.error("Password must be at least 6 characters.");
        return;
      }
    }

    setIsAuthenticating(true);

    try {
      if (authMode === "signup") {
        const registration = portalType === "TPA"
          ? await registerTpaApplicant({
              fullName,
              phone,
              email,
              password,
              organization,
            })
          : await registerUser({ fullName, phone, email, password });
        setPendingChallenge(registration.challenge_id);
        setActivationMessage("");
        toast.success("Verification email accepted by the configured provider.");
      } else {
        await loginUser({
          email,
          password,
        });
        toast.success(`Authenticated as ${email}`);
      }

      if (authMode === "signin") {
        setTimeout(() => {
          setIsAuthenticating(false);
          onAuthenticated();
        }, 600);
      } else {
        setIsAuthenticating(false);
      }
    } catch (err: any) {
      setIsAuthenticating(false);
      toast.error(err.message || "Authentication failed. Please check credentials.");
    }
  };

  const steps = [
    { title: "Extract", desc: "Claims & medical documents", icon: FileText, color: "#06B6D4" },
    { title: "Understand", desc: "Medical & policy intelligence", icon: BrainCircuit, color: "#8B5CF6" },
    { title: "Validate", desc: "Rules, coverage & compliance", icon: Search, color: "#3B82F6" },
    { title: "Enable", desc: "Faster, fairer decisions", icon: Zap, color: "#10B981" },
  ];

  const providerLogos = ["HCG", "Apollo Hospitals", "MAX Healthcare", "Fortis", "Manipal Hospitals"];

  return (
    <div className="relative min-h-screen w-full bg-slate-100 dark:bg-[#080C14] text-slate-900 dark:text-[#F9FAFB] overflow-x-hidden font-sans transition-colors duration-300">
      
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
            className="flex items-center gap-2 rounded-xl border border-slate-300 dark:border-[#1F2937] bg-white dark:bg-[#111827] px-3.5 py-1.5 text-xs font-semibold text-slate-700 dark:text-white shadow-sm transition hover:scale-105"
          >
            {isDark ? (
              <>
                <Sun className="size-4 text-amber-400" />
                <span>Light Mode</span>
              </>
            ) : (
              <>
                <Moon className="size-4 text-slate-700" />
                <span>Dark Mode</span>
              </>
            )}
          </button>
        </div>
      </header>

      {/* ========================================================================= */}
      {/* STAGE 1: INTRO SPLASH */}
      {/* ========================================================================= */}
      <AnimatePresence>
        {showSplash && (
          <motion.div
            key="splash-screen"
            initial={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.6 }}
            className="fixed inset-0 z-50 flex flex-col items-center justify-center bg-[#0B0F17] text-white"
          >
            <div className="relative flex flex-col items-center">
              <motion.div
                initial={{ scale: 0.8 }}
                animate={{ scale: 1 }}
                className="flex size-24 items-center justify-center rounded-2xl bg-gradient-to-br from-[#3B82F6] to-[#06B6D4] shadow-[0_0_50px_rgba(59,130,246,0.5)]"
              >
                <ShieldCheck className="size-12 text-white animate-pulse" />
              </motion.div>
              <h1 className="mt-4 text-2xl font-bold tracking-tight">ClaimBridge AI Core</h1>
              <p className="mt-1 text-xs font-mono text-[#06B6D4]">Loading Medical & Policy Intelligence...</p>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* ========================================================================= */}
      {/* STAGE 2: MAIN HERO & PORTAL LAYOUT */}
      {/* ========================================================================= */}
      <main className="relative z-10 mx-auto max-w-[1700px] p-6 lg:p-12">
        <div className="grid gap-8 lg:grid-cols-12 lg:items-start">
          
          {/* ========================================================================= */}
          {/* LEFT COLUMN: HERO HEADLINE + PROMINENT MEDICAL VISUAL SHOWCASE */}
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

              {/* Animated HUD Grid Overlay */}
              <div className="absolute inset-0 bg-scanline-effect opacity-30 pointer-events-none" />

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

                {/* FLOATING PROMINENT METRICS BADGES */}
                <div className="grid gap-3 sm:grid-cols-3">
                  
                  {/* Badge 1: OCR */}
                  <motion.div
                    animate={{ y: [0, -6, 0] }}
                    transition={{ repeat: Infinity, duration: 4, ease: "easeInOut" }}
                    className="rounded-2xl border border-slate-200 dark:border-[#06B6D4]/40 bg-white/90 dark:bg-[#111827]/90 p-4 backdrop-blur-md shadow-xl"
                  >
                    <div className="flex items-center justify-between text-xs text-slate-500 dark:text-[#9CA3AF]">
                      <span>OCR Extraction Accuracy</span>
                      <CheckCircle2 className="size-4 text-[#10B981]" />
                    </div>
                    <p className="mt-1 text-2xl font-extrabold font-mono text-slate-900 dark:text-white">98.93%</p>
                    <span className="text-[10px] font-semibold text-[#10B981]">Verified Key-Values</span>
                  </motion.div>

                  {/* Badge 2: Policy Match */}
                  <motion.div
                    animate={{ y: [0, -8, 0] }}
                    transition={{ repeat: Infinity, duration: 4.5, delay: 0.3, ease: "easeInOut" }}
                    className="rounded-2xl border border-slate-200 dark:border-[#8B5CF6]/40 bg-white/90 dark:bg-[#111827]/90 p-4 backdrop-blur-md shadow-xl"
                  >
                    <div className="flex items-center justify-between text-xs text-slate-500 dark:text-[#9CA3AF]">
                      <span>Policy Match</span>
                      <BrainCircuit className="size-4 text-purple-600 dark:text-[#8B5CF6]" />
                    </div>
                    <p className="mt-1 text-2xl font-extrabold font-mono text-purple-600 dark:text-[#8B5CF6]">Verified</p>
                    <span className="text-[10px] text-slate-500 dark:text-[#9CA3AF]">RAG Evidence Neural Check</span>
                  </motion.div>

                  {/* Badge 3: Claim Readiness */}
                  <motion.div
                    animate={{ y: [0, -6, 0] }}
                    transition={{ repeat: Infinity, duration: 3.8, delay: 0.6, ease: "easeInOut" }}
                    className="rounded-2xl border border-slate-200 dark:border-[#3B82F6]/40 bg-white/90 dark:bg-[#111827]/90 p-4 backdrop-blur-md shadow-xl"
                  >
                    <div className="flex items-center justify-between text-xs text-slate-500 dark:text-[#9CA3AF]">
                      <span>Claim Readiness Score</span>
                      <Zap className="size-4 text-[#3B82F6]" />
                    </div>
                    <p className="mt-1 text-2xl font-extrabold font-mono text-[#3B82F6]">93%</p>
                    <div className="mt-1.5 h-1.5 w-full rounded-full bg-slate-200 dark:bg-[#1F2937] overflow-hidden">
                      <div className="h-full bg-gradient-to-r from-[#3B82F6] to-[#06B6D4] w-[93%]" />
                    </div>
                  </motion.div>

                </div>

              </div>

            </div>

            {/* STEP-BY-STEP WORKFLOW BAR */}
            <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
              {steps.map((s) => {
                const Icon = s.icon;
                return (
                  <div
                    key={s.title}
                    className="flex items-center gap-3 p-3.5 rounded-2xl border border-slate-200 dark:border-[#1F2937] bg-white dark:bg-[#111827] shadow-sm"
                  >
                    <div
                      className="flex size-9 shrink-0 items-center justify-center rounded-xl"
                      style={{ backgroundColor: `${s.color}20`, color: s.color }}
                    >
                      <Icon className="size-5" />
                    </div>
                    <div>
                      <h4 className="text-xs font-bold text-slate-900 dark:text-white">{s.title}</h4>
                      <p className="text-[10px] text-slate-500 dark:text-[#9CA3AF] leading-tight">{s.desc}</p>
                    </div>
                  </div>
                );
              })}
            </div>

            {/* VALUE PROPS FOOTER */}
            <div className="flex flex-wrap items-center justify-between gap-4 pt-2 text-xs font-semibold text-slate-600 dark:text-[#9CA3AF]">
              <div className="flex items-center gap-2">
                <Zap className="size-4 text-[#3B82F6]" />
                <span>Faster Processing</span>
              </div>
              <div className="flex items-center gap-2">
                <CheckCircle2 className="size-4 text-[#10B981]" />
                <span>Higher Accuracy</span>
              </div>
              <div className="flex items-center gap-2">
                <HeartHandshake className="size-4 text-purple-500" />
                <span>Better Patient Outcomes</span>
              </div>
            </div>

          </div>

          {/* ========================================================================= */}
          {/* RIGHT COLUMN: CLEAN PORTAL ACCESS / AUTHENTICATION PANEL WITH REAL-TIME VALIDATION */}
          {/* ========================================================================= */}
          <div className="lg:col-span-5 space-y-6">
            
            <div className="rounded-3xl border border-slate-300 dark:border-[#1F2937] bg-white dark:bg-[#111827] p-8 shadow-2xl backdrop-blur-xl space-y-6">
              
              {/* Header */}
              <div>
                <span className="font-mono text-xs uppercase tracking-widest text-[#06B6D4] font-semibold">
                  SECURE PORTAL ACCESS
                </span>
                <h2 className="mt-1 text-2xl font-extrabold tracking-tight text-slate-900 dark:text-white sm:text-3xl">
                  {authMode === "signin" ? "Welcome to ClaimBridge" : "Create ClaimBridge Account"}
                </h2>
                <p className="mt-1 text-xs text-slate-500 dark:text-[#9CA3AF]">
                  {authMode === "signin"
                    ? "Select your portal and enter your work credentials to sign in."
                    : "Fill in your details to create your enterprise AI workspace account."}
                </p>
              </div>

              {/* Portal Selection Cards (TPA vs User/Hospital Login) */}
              {!pendingChallenge && <div className="grid grid-cols-2 gap-3">
                
                <button
                  type="button"
                  onClick={() => setPortalType("TPA")}
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
                    <p className="text-xs font-bold text-slate-900 dark:text-white">Claims Officer / TPA</p>
                    <p className="mt-0.5 text-[10px] text-slate-500 dark:text-[#9CA3AF]">
                      Claims, pre-authorizations & settlement ops
                    </p>
                  </div>
                </button>

                <button
                  type="button"
                  onClick={() => setPortalType("Claimant")}
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
                    <p className="text-xs font-bold text-slate-900 dark:text-white">Claimant</p>
                    <p className="mt-0.5 text-[10px] text-slate-500 dark:text-[#9CA3AF]">
                      Submit and track your own claims
                    </p>
                  </div>
                </button>

              </div>}

              {/* Login / Register Form */}
              <form onSubmit={handleSubmit} className="space-y-4">
                {pendingChallenge ? (
                  <div className="space-y-4">
                    <p className="text-sm text-slate-600 dark:text-[#9CA3AF]">
                      Enter the verification code sent to {email}. The code expires in 10 minutes.
                    </p>
                    <input
                      type="text"
                      inputMode="numeric"
                      autoComplete="one-time-code"
                      pattern="[0-9]{6}"
                      maxLength={6}
                      value={otpCode}
                      onChange={(event) => setOtpCode(event.target.value.replace(/\D/g, ""))}
                      aria-label="Six-digit email verification code"
                      required
                      className="h-12 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 text-center font-mono text-lg tracking-[0.5em] text-slate-900 outline-none focus:border-[#3B82F6] dark:border-[#1F2937] dark:bg-[#0B0F17] dark:text-white"
                      placeholder="000000"
                    />
                    {activationMessage && (
                      <p className="rounded-lg bg-amber-500/10 p-3 text-xs text-amber-700 dark:text-amber-300">
                        {activationMessage}
                      </p>
                    )}
                    <button
                      type="button"
                      onClick={async () => {
                        try {
                          await resendEmailOtp(email);
                          toast.success("If the account is eligible, a verification email will be sent.");
                        } catch (err: any) {
                          toast.error(err.message || "Could not request another code.");
                        }
                      }}
                      className="text-xs font-semibold text-[#3B82F6] hover:underline"
                    >
                      Resend verification email
                    </button>
                  </div>
                ) : (
                  <>
                
                {/* CREATE ACCOUNT EXTRA FIELDS */}
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
                      {touched["fullName"] && !fullName.trim() && (
                        <p className="text-[11px] text-red-500 flex items-center gap-1">
                          <AlertCircle className="size-3" /> Full Name is required.
                        </p>
                      )}
                    </div>

                    <div className="space-y-1.5">
                      <label className="text-xs font-semibold text-slate-600 dark:text-[#9CA3AF]">
                        Phone number <span className="text-red-500">*</span>
                      </label>
                      <input
                        type="tel"
                        autoComplete="tel"
                        value={phone}
                        onChange={(event) => setPhone(event.target.value)}
                        required
                        pattern="\+?[0-9]{8,15}"
                        className="h-11 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 text-sm text-slate-900 outline-none focus:border-[#3B82F6] dark:border-[#1F2937] dark:bg-[#0B0F17] dark:text-white"
                        placeholder="+15555550123"
                      />
                    </div>
                    {portalType === "TPA" && (
                      <div className="space-y-1.5">
                        <label className="text-xs font-semibold text-slate-600 dark:text-[#9CA3AF]">
                          TPA organization (pending trusted verification) <span className="text-red-500">*</span>
                        </label>
                        <input
                          type="text"
                          value={organization}
                          onChange={(event) => setOrganization(event.target.value)}
                          required
                          maxLength={150}
                          className="h-11 w-full rounded-xl border border-slate-200 bg-slate-50 px-4 text-sm text-slate-900 outline-none focus:border-[#3B82F6] dark:border-[#1F2937] dark:bg-[#0B0F17] dark:text-white"
                          placeholder="Official TPA organization"
                        />
                        <p className="text-[11px] text-slate-500 dark:text-[#9CA3AF]">
                          Entering an organization does not grant officer access. A trusted provisioner must authorize it.
                        </p>
                      </div>
                    )}
                  </>
                )}

                {/* USER ID / EMAIL ADDRESS FIELD */}
                <div className="space-y-1.5">
                  <label className="text-xs font-semibold text-slate-600 dark:text-[#9CA3AF]">
                    User ID / Email Address <span className="text-red-500">*</span>
                  </label>
                  <input
                    type="text"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    onBlur={() => handleBlur("email")}
                    required
                    className={`h-11 w-full rounded-xl border px-4 text-sm text-slate-900 dark:text-white bg-slate-50 dark:bg-[#0B0F17] outline-none transition ${
                      touched["email"] && !isValidIdentifier
                        ? "border-red-500 focus:border-red-500"
                        : "border-slate-200 dark:border-[#1F2937] focus:border-[#3B82F6]"
                    }`}
                    placeholder="name@example.com"
                  />
                  {touched["email"] && !isValidIdentifier && (
                    <p className="text-[11px] text-red-500 flex items-center gap-1">
                      <AlertCircle className="size-3" /> Enter a valid email address.
                    </p>
                  )}
                </div>

                {/* PASSWORD FIELD WITH LIVE STRENGTH VALIDATION */}
                <div className="space-y-1.5">
                  <div className="flex justify-between text-xs">
                    <label className="font-semibold text-slate-600 dark:text-[#9CA3AF]">
                      Password <span className="text-red-500">*</span>
                    </label>
                    {authMode === "signin" && (
                      <a href="#forgot" onClick={(e) => e.preventDefault()} className="text-[#3B82F6] hover:underline">
                        Forgot password?
                      </a>
                    )}
                  </div>
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    onBlur={() => handleBlur("password")}
                    required
                    className={`h-11 w-full rounded-xl border px-4 text-sm text-slate-900 dark:text-white bg-slate-50 dark:bg-[#0B0F17] outline-none transition ${
                      touched["password"] && authMode === "signup" && !isStrongPassword
                        ? "border-amber-500 focus:border-amber-500"
                        : "border-slate-200 dark:border-[#1F2937] focus:border-[#3B82F6]"
                    }`}
                    placeholder="Enter strong password"
                  />

                  {/* LIVE PASSWORD STRENGTH INDICATORS (FOR SIGN UP) */}
                  {authMode === "signup" && password.length > 0 && (
                    <div className="mt-2 space-y-2 rounded-xl border border-slate-200 dark:border-[#1F2937] bg-slate-50 dark:bg-[#0B0F17] p-3 text-xs">
                      <div className="flex items-center justify-between">
                        <span className="text-[11px] text-slate-500 dark:text-[#9CA3AF]">Password Strength:</span>
                        <span
                          className={`font-mono font-bold text-[11px] ${
                            strengthScore <= 2
                              ? "text-red-500"
                              : strengthScore === 3
                              ? "text-amber-500"
                              : "text-emerald-500"
                          }`}
                        >
                          {strengthScore <= 2 ? "Weak" : strengthScore === 3 ? "Medium" : "Strong & Valid"}
                        </span>
                      </div>

                      {/* Visual Strength Meter Bar */}
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

                      {/* Rule Checklist Pills */}
                      <div className="grid grid-cols-2 gap-1.5 pt-1 text-[10px]">
                        <span className={`flex items-center gap-1 ${isMinLength ? "text-emerald-500 font-semibold" : "text-slate-400"}`}>
                          {isMinLength ? <Check className="size-3" /> : <X className="size-3" />} 12+ Characters
                        </span>
                        <span className={`flex items-center gap-1 ${hasUpper ? "text-emerald-500 font-semibold" : "text-slate-400"}`}>
                          {hasUpper ? <Check className="size-3" /> : <X className="size-3" />} Uppercase (A-Z)
                        </span>
                        <span className={`flex items-center gap-1 ${hasLower ? "text-emerald-500 font-semibold" : "text-slate-400"}`}>
                          {hasLower ? <Check className="size-3" /> : <X className="size-3" />} Lowercase (a-z)
                        </span>
                        <span className={`flex items-center gap-1 ${hasSpecialOrNum ? "text-emerald-500 font-semibold" : "text-slate-400"}`}>
                          {hasSpecialOrNum ? <Check className="size-3" /> : <X className="size-3" />} Special / Number
                        </span>
                      </div>
                    </div>
                  )}
                </div>

                {/* CONFIRM PASSWORD FIELD */}
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
                      className={`h-11 w-full rounded-xl border px-4 text-sm text-slate-900 dark:text-white bg-slate-50 dark:bg-[#0B0F17] outline-none transition ${
                        touched["confirmPassword"] && !isPasswordMatch
                          ? "border-red-500 focus:border-red-500"
                          : "border-slate-200 dark:border-[#1F2937] focus:border-[#3B82F6]"
                      }`}
                      placeholder="Re-enter password to confirm"
                    />
                    {touched["confirmPassword"] && !isPasswordMatch && (
                      <p className="text-[11px] text-red-500 flex items-center gap-1">
                        <AlertCircle className="size-3" /> Passwords do not match.
                      </p>
                    )}
                  </div>
                )}

                {/* Submit Action Button */}
                <button
                  type="submit"
                  disabled={isAuthenticating}
                  className="group flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-gradient-to-r from-[#3B82F6] to-[#06B6D4] font-bold text-white shadow-lg shadow-[#3B82F6]/30 hover:shadow-xl transition disabled:opacity-60"
                >
                  {isAuthenticating ? (
                    <span>Processing...</span>
                  ) : pendingChallenge ? (
                    <span>Verify Email</span>
                  ) : authMode === "signin" ? (
                    <>
                      <span>Sign In</span>
                      <ArrowRight className="size-4 transition-transform group-hover:translate-x-1" />
                    </>
                  ) : (
                    <>
                      <span>Create Account</span>
                      <UserPlus className="size-4" />
                    </>
                  )}
                </button>
                  </>
                )}
              </form>

              {/* TOGGLE BETWEEN SIGN IN & CREATE ACCOUNT */}
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
