"use client";

import React from "react";
import { cn } from "@/lib/utils";
import { motion } from "framer-motion";

/* ── Card ──────────────────────────────────────────────────────────── */

interface CardProps extends React.HTMLAttributes<HTMLDivElement> {
  hover?: boolean;
}

export function Card({ className, hover, children, ...props }: CardProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 8 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      className={cn(hover ? "card-hover" : "card", className)}
      {...(props as React.ComponentProps<typeof motion.div>)}
    >
      {children}
    </motion.div>
  );
}

/* ── Metric card ───────────────────────────────────────────────────── */

interface MetricCardProps {
  label: string;
  value: string;
  sub?: string;
  icon?: React.ReactNode;
  color?: string;
}

export function MetricCard({ label, value, sub, icon, color }: MetricCardProps) {
  return (
    <Card className="flex items-start gap-3">
      {icon && (
        <div className={cn("p-2 rounded-lg bg-neutral-800", color)}>
          {icon}
        </div>
      )}
      <div className="min-w-0">
        <p className="text-xs text-neutral-500 uppercase tracking-wider mb-1">{label}</p>
        <p className="text-xl font-semibold text-white truncate">{value}</p>
        {sub && <p className="text-xs text-neutral-400 mt-0.5">{sub}</p>}
      </div>
    </Card>
  );
}

/* ── Spinner ───────────────────────────────────────────────────────── */

export function Spinner({ className }: { className?: string }) {
  return (
    <div className={cn("flex items-center justify-center py-12", className)}>
      <div className="h-8 w-8 rounded-full border-2 border-neutral-700 border-t-accent animate-spin" />
    </div>
  );
}

/* ── Empty State ───────────────────────────────────────────────────── */

interface EmptyProps {
  title: string;
  description?: string;
  action?: React.ReactNode;
}

export function EmptyState({ title, description, action }: EmptyProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 text-center">
      <div className="h-12 w-12 rounded-full bg-neutral-800 flex items-center justify-center mb-4">
        <div className="h-6 w-6 rounded-full bg-neutral-700" />
      </div>
      <h3 className="text-lg font-medium text-neutral-300">{title}</h3>
      {description && <p className="text-sm text-neutral-500 mt-1 max-w-sm">{description}</p>}
      {action && <div className="mt-4">{action}</div>}
    </div>
  );
}

/* ── Badge ─────────────────────────────────────────────────────────── */

interface BadgeProps {
  children: React.ReactNode;
  variant?: "default" | "success" | "warning" | "danger";
}

export function Badge({ children, variant = "default" }: BadgeProps) {
  const styles = {
    default: "bg-neutral-800 text-neutral-300",
    success: "bg-emerald-500/10 text-emerald-400 border border-emerald-500/20",
    warning: "bg-amber-500/10 text-amber-400 border border-amber-500/20",
    danger: "bg-red-500/10 text-red-400 border border-red-500/20",
  };
  return <span className={cn("badge", styles[variant])}>{children}</span>;
}

/* ── Section Header ────────────────────────────────────────────────── */

export function SectionHeader({ title, subtitle, action }: { title: string; subtitle?: string; action?: React.ReactNode }) {
  return (
    <div className="flex items-end justify-between mb-6">
      <div>
        <h2 className="text-xl font-semibold text-white">{title}</h2>
        {subtitle && <p className="text-sm text-neutral-500 mt-0.5">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}
