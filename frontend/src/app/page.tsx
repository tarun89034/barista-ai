"use client";

import React, { useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";
import {
  DollarSign,
  TrendingUp,
  TrendingDown,
  ShieldAlert,
  ArrowRightLeft,
  RefreshCw,
  Loader2,
} from "lucide-react";

import {
  portfolioApi,
  analysisApi,
  marketApi,
  type PortfolioSummary,
  type RiskAnalysisResult,
  type GlobalIndicesResult,
  type GlobalIndexEntry,
} from "@/lib/api";
import { formatCurrency, formatPercent, formatCompact } from "@/lib/utils";
import { Card, MetricCard, Spinner, EmptyState, Badge, SectionHeader } from "@/components/ui";
import { AllocationPie } from "@/components/charts";

/* ── Inline section spinner ─────────────────────────────────────────── */
function SectionSpinner({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-2 py-6 justify-center text-neutral-500 text-sm">
      <Loader2 className="h-4 w-4 animate-spin" />
      <span>{label}</span>
    </div>
  );
}

export default function DashboardPage() {
  const [portfolio, setPortfolio] = useState<PortfolioSummary | null>(null);
  const [risk, setRisk] = useState<RiskAnalysisResult | null>(null);
  const [globalIndices, setGlobalIndices] = useState<GlobalIndicesResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [riskLoading, setRiskLoading] = useState(false);
  const [indicesLoading, setIndicesLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /* ── Step 1: Load portfolio (fast) ──────────────────────────────── */
  const loadPortfolio = useCallback(async (pid?: string) => {
    setLoading(true);
    setError(null);
    try {
      let p: PortfolioSummary;
      if (pid) {
        p = await portfolioApi.get(pid);
      } else {
        const list = await portfolioApi.list();
        if (list.count > 0) {
          p = list.portfolios[0];
        } else {
          p = await portfolioApi.loadSample();
        }
      }
      setPortfolio(p);
      return p;
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load data");
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  /* ── Step 2: Load supplementary data in background ──────────────── */
  const loadRisk = useCallback(async (pid: string) => {
    setRiskLoading(true);
    try {
      const result = await analysisApi.risk(pid);
      setRisk(result);
    } catch {
      /* non-blocking — risk just won't show */
    } finally {
      setRiskLoading(false);
    }
  }, []);

  const loadIndices = useCallback(async () => {
    setIndicesLoading(true);
    try {
      const result = await marketApi.globalIndices();
      setGlobalIndices(result);
    } catch {
      /* non-blocking */
    } finally {
      setIndicesLoading(false);
    }
  }, []);

  /* ── Orchestrate: portfolio first, then background loads ────────── */
  const loadAll = useCallback(async (pid?: string) => {
    const p = await loadPortfolio(pid);
    if (p) {
      // Fire both in parallel, but don't await — let them stream in
      loadRisk(p.portfolio_id);
      loadIndices();
    }
  }, [loadPortfolio, loadRisk, loadIndices]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  if (loading) return <Spinner />;

  if (error) {
    return (
      <EmptyState
        title="Error loading dashboard"
        description={error}
        action={<button onClick={() => loadAll()} className="btn-primary">Retry</button>}
      />
    );
  }

  if (!portfolio) {
    return (
      <EmptyState
        title="No portfolio loaded"
        description="Load a sample portfolio or upload your own to get started."
        action={<button onClick={() => loadAll()} className="btn-primary">Load Sample Portfolio</button>}
      />
    );
  }

  const gainLoss = portfolio.total_current_value - portfolio.total_purchase_value;
  const gainLossPct = portfolio.total_purchase_value > 0 ? gainLoss / portfolio.total_purchase_value : 0;
  const riskLevel = risk?.risk_summary?.risk_level ?? "N/A";
  const volatility = risk?.portfolio_metrics?.volatility as number | undefined;
  const sharpe = risk?.portfolio_metrics?.sharpe_ratio as number | undefined;

  // Build allocation pie data
  const allocationMap: Record<string, number> = {};
  for (const a of portfolio.assets) {
    const val = a.current_value ?? a.quantity * a.purchase_price;
    allocationMap[a.asset_type] = (allocationMap[a.asset_type] ?? 0) + val;
  }
  const total = Object.values(allocationMap).reduce((s, v) => s + v, 0);
  const pieData = Object.entries(allocationMap).map(([name, value]) => ({
    name,
    value: total > 0 ? value / total : 0,
  }));

  // Global indices
  const indexEntries = globalIndices?.indices
    ? Object.entries(globalIndices.indices) as [string, GlobalIndexEntry][]
    : [];

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <motion.h1 initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} className="text-2xl font-bold text-white">
            Dashboard
          </motion.h1>
          <p className="text-sm text-neutral-500 mt-1">{portfolio.name} &middot; {portfolio.asset_count} assets</p>
        </div>
        <button onClick={() => loadAll(portfolio.portfolio_id)} className="btn-ghost flex items-center gap-2">
          <RefreshCw className="h-4 w-4" /> Refresh
        </button>
      </div>

      {/* Key Metrics */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <MetricCard label="Portfolio Value" value={formatCurrency(portfolio.total_current_value)} sub={`Cost basis: ${formatCurrency(portfolio.total_purchase_value)}`} icon={<DollarSign className="h-5 w-5 text-accent" />} />
        <MetricCard label="Total Gain/Loss" value={formatCurrency(gainLoss)} sub={`${gainLoss >= 0 ? "+" : ""}${formatPercent(gainLossPct)}`} icon={<TrendingUp className="h-5 w-5 text-accent" />} color={gainLoss >= 0 ? "text-success" : "text-danger"} />
        <MetricCard
          label="Risk Level"
          value={riskLoading ? "..." : riskLevel}
          sub={riskLoading ? "Analyzing..." : (volatility != null ? `Volatility: ${formatPercent(volatility)}` : undefined)}
          icon={<ShieldAlert className="h-5 w-5 text-accent" />}
        />
        <MetricCard
          label="Sharpe Ratio"
          value={riskLoading ? "..." : (sharpe != null ? sharpe.toFixed(2) : "N/A")}
          sub="Risk-adjusted return"
          icon={<ArrowRightLeft className="h-5 w-5 text-accent" />}
        />
      </div>

      {/* Global Market Indices Widget */}
      {indicesLoading ? (
        <Card>
          <SectionHeader title="Global Markets" subtitle="Major world indices" />
          <SectionSpinner label="Loading global indices..." />
        </Card>
      ) : indexEntries.length > 0 ? (
        <Card>
          <SectionHeader title="Global Markets" subtitle="Major world indices" />
          <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-6 gap-3">
            {indexEntries.map(([symbol, idx], i) => (
              <motion.div
                key={symbol}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.04 }}
                className="p-3 rounded-lg bg-neutral-800/40 border border-neutral-700/40"
              >
                <div className="text-xs text-neutral-500 truncate">{idx.name}</div>
                <div className="text-sm font-mono text-white mt-1">{formatCompact(idx.price)}</div>
                <div className={`text-xs font-mono mt-0.5 flex items-center gap-1 ${idx.change_pct >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                  {idx.change_pct >= 0 ? <TrendingUp className="h-3 w-3" /> : <TrendingDown className="h-3 w-3" />}
                  {idx.change_pct >= 0 ? "+" : ""}{idx.change_pct.toFixed(2)}%
                </div>
                <div className="text-[10px] text-neutral-600 mt-1">{idx.region} &middot; {idx.currency}</div>
              </motion.div>
            ))}
          </div>
        </Card>
      ) : null}

      {/* Charts + Findings */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card>
          <SectionHeader title="Asset Allocation" subtitle="By asset type" />
          <AllocationPie data={pieData} />
        </Card>

        <Card>
          <SectionHeader title="Key Findings" subtitle={risk ? `As of ${new Date(risk.timestamp).toLocaleString()}` : undefined} />
          {riskLoading ? (
            <SectionSpinner label="Running risk analysis..." />
          ) : risk?.risk_summary?.key_findings?.length ? (
            <ul className="space-y-3">
              {risk.risk_summary.key_findings.map((f, i) => (
                <motion.li key={i} initial={{ opacity: 0, x: -5 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.08 }} className="flex items-start gap-3 text-sm text-neutral-300">
                  <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-accent flex-shrink-0" />
                  {f}
                </motion.li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-neutral-500">No findings yet. Run an analysis to see results.</p>
          )}
          {riskLevel && riskLevel !== "N/A" && (
            <div className="mt-6">
              <Badge variant={riskLevel === "LOW" ? "success" : riskLevel === "HIGH" ? "danger" : "warning"}>{riskLevel} RISK</Badge>
            </div>
          )}
        </Card>
      </div>

      {/* Holdings Table */}
      <Card>
        <SectionHeader title="Holdings" subtitle={`${portfolio.asset_count} positions`} />
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-neutral-500 text-xs uppercase tracking-wider border-b border-neutral-800">
                <th className="text-left py-3 pr-4">Asset</th>
                <th className="text-left py-3 pr-4">Type</th>
                <th className="text-right py-3 pr-4">Qty</th>
                <th className="text-right py-3 pr-4">Price</th>
                <th className="text-right py-3 pr-4">Value</th>
                <th className="text-right py-3">Gain/Loss</th>
              </tr>
            </thead>
            <tbody>
              {portfolio.assets.map((a, i) => {
                const val = a.current_value ?? a.quantity * a.purchase_price;
                const cost = a.quantity * a.purchase_price;
                const gl = val - cost;
                return (
                  <motion.tr key={a.symbol} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.03 }} className="border-b border-neutral-800/50 hover:bg-neutral-800/30 transition-colors">
                    <td className="py-3 pr-4">
                      <div className="font-medium text-white">{a.symbol}</div>
                      <div className="text-xs text-neutral-500">{a.name}</div>
                    </td>
                    <td className="py-3 pr-4"><Badge>{a.asset_type}</Badge></td>
                    <td className="text-right py-3 pr-4 text-neutral-300 font-mono">{a.quantity}</td>
                    <td className="text-right py-3 pr-4 text-neutral-300 font-mono">{formatCurrency(a.current_price ?? a.purchase_price)}</td>
                    <td className="text-right py-3 pr-4 text-white font-mono font-medium">{formatCurrency(val)}</td>
                    <td className={`text-right py-3 font-mono font-medium ${gl >= 0 ? "text-success" : "text-danger"}`}>{gl >= 0 ? "+" : ""}{formatCurrency(gl)}</td>
                  </motion.tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}
