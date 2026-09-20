import React from "react";
import { Zap, ShieldCheck, FileCheck2, Activity, CheckCircle2, AlertTriangle } from "lucide-react";

interface ReadinessGaugeProps {
  score: number; // e.g. 89.47
  validationScore?: number; // e.g. 100
  medicalScore?: number; // e.g. 70
  policyScore?: number; // e.g. 88.5
  ocrScore?: number; // e.g. 98.9
}

export function ReadinessGauge({
  score = 89.47,
  validationScore = 100,
  medicalScore = 70,
  policyScore = 88.5,
  ocrScore = 98.93,
}: ReadinessGaugeProps) {
  // SVG Radial Gauge Calculations
  const radius = 80;
  const stroke = 12;
  const normalizedRadius = radius - stroke * 0.5;
  const circumference = normalizedRadius * 2 * Math.PI;
  const strokeDashoffset = circumference - (score / 100) * circumference;

  return (
    <div className="flex flex-col gap-6 rounded-2xl border border-[#1F2937] bg-[#111827] p-6 shadow-xl lg:flex-row lg:items-center">
      
      {/* CIRCULAR RADIAL SCORE GAUGE */}
      <div className="flex flex-col items-center justify-center p-4">
        <div className="relative flex size-52 items-center justify-center">
          <svg height={radius * 2} width={radius * 2} className="rotate-[-90deg]">
            {/* Background Ring */}
            <circle
              stroke="#1F2937"
              fill="transparent"
              strokeWidth={stroke}
              r={normalizedRadius}
              cx={radius}
              cy={radius}
            />
            {/* Animated Glow Score Ring */}
            <circle
              stroke="url(#neonScoreGradient)"
              fill="transparent"
              strokeWidth={stroke}
              strokeDasharray={`${circumference} ${circumference}`}
              style={{ strokeDashoffset }}
              strokeLinecap="round"
              r={normalizedRadius}
              cx={radius}
              cy={radius}
              className="transition-all duration-1000 ease-out"
            />
            <defs>
              <linearGradient id="neonScoreGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                <stop offset="0%" stopColor="#3B82F6" />
                <stop offset="50%" stopColor="#06B6D4" />
                <stop offset="100%" stopColor="#10B981" />
              </linearGradient>
            </defs>
          </svg>

          {/* Inner Content */}
          <div className="absolute inset-0 flex flex-col items-center justify-center text-center">
            <Zap className="size-6 text-[#06B6D4] animate-pulse" />
            <span className="mt-1 text-3xl font-extrabold font-mono text-white tracking-tight">
              {score.toFixed(2)}%
            </span>
            <span className="text-[10px] font-mono text-[#9CA3AF] uppercase tracking-wider">
              Claim Readiness
            </span>
          </div>
        </div>
      </div>

      {/* COMPONENT SCORES BREAKDOWN GRID */}
      <div className="flex-1 space-y-4">
        <div>
          <h3 className="text-base font-bold text-white">Claim Readiness Component Breakdown</h3>
          <p className="text-xs text-[#9CA3AF]">
            Multi-engine weighted synthesis for autonomous submission qualification
          </p>
        </div>

        <div className="grid gap-3 sm:grid-cols-2">
          
          {/* Validation Score */}
          <div className="rounded-xl border border-[#1F2937] bg-[#0B0F17]/60 p-3.5">
            <div className="flex items-center justify-between text-xs">
              <span className="text-[#9CA3AF]">Cross-Validation Engine</span>
              <span className="font-mono font-bold text-[#10B981]">{validationScore}%</span>
            </div>
            <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-[#1F2937]">
              <div className="h-full rounded-full bg-[#10B981]" style={{ width: `${validationScore}%` }} />
            </div>
          </div>

          {/* OCR Score */}
          <div className="rounded-xl border border-[#1F2937] bg-[#0B0F17]/60 p-3.5">
            <div className="flex items-center justify-between text-xs">
              <span className="text-[#9CA3AF]">OCR Document Extraction</span>
              <span className="font-mono font-bold text-[#06B6D4]">{ocrScore}%</span>
            </div>
            <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-[#1F2937]">
              <div className="h-full rounded-full bg-[#06B6D4]" style={{ width: `${ocrScore}%` }} />
            </div>
          </div>

          {/* Policy RAG Score */}
          <div className="rounded-xl border border-[#1F2937] bg-[#0B0F17]/60 p-3.5">
            <div className="flex items-center justify-between text-xs">
              <span className="text-[#9CA3AF]">Policy RAG Verification</span>
              <span className="font-mono font-bold text-[#8B5CF6]">{policyScore}%</span>
            </div>
            <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-[#1F2937]">
              <div className="h-full rounded-full bg-[#8B5CF6]" style={{ width: `${policyScore}%` }} />
            </div>
          </div>

          {/* Medical Score */}
          <div className="rounded-xl border border-[#1F2937] bg-[#0B0F17]/60 p-3.5">
            <div className="flex items-center justify-between text-xs">
              <span className="text-[#9CA3AF]">Medical Intelligence Score</span>
              <span className="font-mono font-bold text-[#F59E0B]">{medicalScore}%</span>
            </div>
            <div className="mt-2 h-1.5 w-full overflow-hidden rounded-full bg-[#1F2937]">
              <div className="h-full rounded-full bg-[#F59E0B]" style={{ width: `${medicalScore}%` }} />
            </div>
          </div>

        </div>
      </div>

    </div>
  );
}
