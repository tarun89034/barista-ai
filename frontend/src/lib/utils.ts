import { clsx, type ClassValue } from "clsx";

export function cn(...inputs: ClassValue[]) {
  return clsx(inputs);
}

export function formatCurrency(value: number | null | undefined, currency = "USD", decimals = 2): string {
  if (value == null) return "N/A";
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency,
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  }).format(value);
}

export function formatPercent(value: number | null | undefined, decimals = 2): string {
  if (value == null) return "N/A";
  return `${(value * 100).toFixed(decimals)}%`;
}

export function formatNumber(value: number | null | undefined, decimals = 2): string {
  if (value == null) return "N/A";
  return value.toFixed(decimals);
}

export function formatCompact(value: number | null | undefined): string {
  if (value == null) return "N/A";
  return new Intl.NumberFormat("en-US", {
    notation: "compact",
    maximumFractionDigits: 2,
  }).format(value);
}

export function riskColor(level: string): string {
  switch (level?.toUpperCase()) {
    case "LOW":
      return "text-success";
    case "MODERATE":
      return "text-warning";
    case "HIGH":
      return "text-danger";
    default:
      return "text-neutral-400";
  }
}

export function riskBgColor(level: string): string {
  switch (level?.toUpperCase()) {
    case "LOW":
      return "bg-emerald-500/10 border-emerald-500/20";
    case "MODERATE":
      return "bg-amber-500/10 border-amber-500/20";
    case "HIGH":
      return "bg-red-500/10 border-red-500/20";
    default:
      return "bg-neutral-500/10 border-neutral-500/20";
  }
}
