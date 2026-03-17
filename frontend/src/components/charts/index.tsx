"use client";

import React from "react";
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  Legend,
} from "recharts";

// eslint-disable-next-line @typescript-eslint/no-explicit-any
const pctFormatter = (decimals: number) => (value: any) =>
  `${(Number(value) * 100).toFixed(decimals)}%`;

const COLORS = [
  "#6366f1", "#8b5cf6", "#a78bfa", "#c4b5fd",
  "#22c55e", "#f59e0b", "#ef4444", "#06b6d4",
  "#ec4899", "#84cc16",
];

/* ── Allocation Pie ────────────────────────────────────────────────── */

interface PieDataItem {
  name: string;
  value: number;
}

export function AllocationPie({ data }: { data: PieDataItem[] }) {
  return (
    <ResponsiveContainer width="100%" height={280}>
      <PieChart>
        <Pie
          data={data}
          cx="50%"
          cy="50%"
          innerRadius={65}
          outerRadius={110}
          paddingAngle={2}
          dataKey="value"
          stroke="none"
        >
          {data.map((_, i) => (
            <Cell key={i} fill={COLORS[i % COLORS.length]} />
          ))}
        </Pie>
        <Tooltip
          contentStyle={{
            background: "#1f1f1f",
            border: "1px solid #404040",
            borderRadius: 8,
            fontSize: 12,
          }}
          formatter={pctFormatter(1)}
        />
        <Legend
          formatter={(value: string) => (
            <span className="text-xs text-neutral-400">{value}</span>
          )}
        />
      </PieChart>
    </ResponsiveContainer>
  );
}

/* ── Risk Metrics Bar ──────────────────────────────────────────────── */

interface BarDataItem {
  name: string;
  value: number;
}

export function MetricsBar({ data, label }: { data: BarDataItem[]; label?: string }) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
        <XAxis
          dataKey="name"
          tick={{ fill: "#a3a3a3", fontSize: 11 }}
          axisLine={{ stroke: "#404040" }}
          tickLine={false}
        />
        <YAxis
          tick={{ fill: "#a3a3a3", fontSize: 11 }}
          axisLine={{ stroke: "#404040" }}
          tickLine={false}
          tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
        />
        <Tooltip
          contentStyle={{
            background: "#1f1f1f",
            border: "1px solid #404040",
            borderRadius: 8,
            fontSize: 12,
          }}
          formatter={pctFormatter(2)}
        />
        <Bar dataKey="value" fill="#6366f1" radius={[4, 4, 0, 0]} name={label ?? "Value"} />
      </BarChart>
    </ResponsiveContainer>
  );
}

/* ── Drift Bar (positive/negative) ─────────────────────────────────── */

export function DriftBar({ data }: { data: { name: string; drift: number }[] }) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <BarChart data={data} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#262626" />
        <XAxis
          dataKey="name"
          tick={{ fill: "#a3a3a3", fontSize: 11 }}
          axisLine={{ stroke: "#404040" }}
          tickLine={false}
        />
        <YAxis
          tick={{ fill: "#a3a3a3", fontSize: 11 }}
          axisLine={{ stroke: "#404040" }}
          tickLine={false}
          tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
        />
        <Tooltip
          contentStyle={{
            background: "#1f1f1f",
            border: "1px solid #404040",
            borderRadius: 8,
            fontSize: 12,
          }}
          formatter={pctFormatter(2)}
        />
        <Bar dataKey="drift" name="Drift" radius={[4, 4, 0, 0]}>
          {data.map((entry, i) => (
            <Cell key={i} fill={entry.drift > 0 ? "#ef4444" : "#22c55e"} />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
