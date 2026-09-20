import { createFileRoute } from "@tanstack/react-router";
import React from "react";
import { BarChart3, TrendingUp, PieChart, Activity, Zap, FileText } from "lucide-react";
import {
  AreaChart,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  BarChart as ReBarChart,
  Bar,
} from "recharts";
import { AppLayout } from "@/components/layout/AppLayout";

export const Route = createFileRoute("/analytics")({
  head: () => ({
    meta: [
      { title: "Portfolio Analytics — ClaimBridge" },
      {
        name: "description",
        content: "Portfolio volume analytics, loss ratio trends and AI verification metrics.",
      },
    ],
  }),
  component: AnalyticsPage,
});

const monthlyData = [
  { month: "Jan", volume: 3200, approved: 2900, review: 300 },
  { month: "Feb", volume: 3800, approved: 3400, review: 400 },
  { month: "Mar", volume: 4100, approved: 3700, review: 400 },
  { month: "Apr", volume: 4900, approved: 4400, review: 500 },
  { month: "May", volume: 5400, approved: 4800, review: 600 },
  { month: "Jun", volume: 6100, approved: 5500, review: 600 },
  { month: "Jul", volume: 6800, approved: 6100, review: 700 },
  { month: "Aug", volume: 7400, approved: 6700, review: 700 },
  { month: "Sep", volume: 8200, approved: 7500, review: 700 },
];

function AnalyticsPage() {
  return (
    <AppLayout
      title="Portfolio Analytics & Reporting"
      breadcrumbs={[{ label: "Dashboard", href: "/" }, { label: "Analytics" }]}
    >
      <div className="space-y-8">
        
        {/* HEADER */}
        <div className="flex flex-col justify-between gap-4 sm:flex-row sm:items-center">
          <div>
            <h1 className="text-2xl font-extrabold text-slate-900 dark:text-white">Portfolio Analytics</h1>
            <p className="text-xs text-slate-500 dark:text-[#9CA3AF]">
              Real-time claim turnaround metrics, loss ratios & AI accuracy breakdown.
            </p>
          </div>
        </div>

        {/* CHARTS GRID */}
        <div className="grid gap-6 lg:grid-cols-2">
          
          {/* Chart 1: Volume Trend */}
          <div className="rounded-2xl border border-slate-200 dark:border-[#1F2937] bg-white dark:bg-[#111827] p-6 shadow-xl space-y-4">
            <h3 className="text-base font-bold text-slate-900 dark:text-white">Monthly Intake vs Auto-Approved</h3>
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <AreaChart data={monthlyData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1F2937" />
                  <XAxis dataKey="month" stroke="#9CA3AF" />
                  <YAxis stroke="#9CA3AF" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#0B0F17",
                      borderColor: "#1F2937",
                      color: "#F9FAFB",
                    }}
                  />
                  <Area type="monotone" dataKey="volume" stroke="#06B6D4" fill="#06B6D4" fillOpacity={0.2} name="Total Volume" />
                  <Area type="monotone" dataKey="approved" stroke="#10B981" fill="#10B981" fillOpacity={0.3} name="Auto Approved" />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          </div>

          {/* Chart 2: Human Review Triage Reasons */}
          <div className="rounded-2xl border border-slate-200 dark:border-[#1F2937] bg-white dark:bg-[#111827] p-6 shadow-xl space-y-4">
            <h3 className="text-base font-bold text-slate-900 dark:text-white">Review Triage Count</h3>
            <div className="h-72 w-full">
              <ResponsiveContainer width="100%" height="100%">
                <ReBarChart data={monthlyData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#1F2937" />
                  <XAxis dataKey="month" stroke="#9CA3AF" />
                  <YAxis stroke="#9CA3AF" />
                  <Tooltip
                    contentStyle={{
                      backgroundColor: "#0B0F17",
                      borderColor: "#1F2937",
                      color: "#F9FAFB",
                    }}
                  />
                  <Bar dataKey="review" fill="#F59E0B" radius={[6, 6, 0, 0]} name="Human Review Count" />
                </ReBarChart>
              </ResponsiveContainer>
            </div>
          </div>

        </div>

      </div>
    </AppLayout>
  );
}
