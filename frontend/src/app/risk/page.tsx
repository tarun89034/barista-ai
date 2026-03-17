"use client";

import React, { useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";
import { ShieldAlert, RefreshCw } from "lucide-react";

import { portfolioApi, analysisApi, type PortfolioSummary, type RiskAnalysisResult } from "@/lib/api";
import { formatPercent, formatNumber } from "@/lib/utils";
import { Card, MetricCard, Spinner, EmptyState, SectionHeader } from "@/components/ui";
import { MetricsBar } from "@/components/charts";

export default function RiskPage() {
  const [portfolio, setPortfolio] = useState<PortfolioSummary | null>(null);
  const [risk, setRisk] = useState<RiskAnalysisResult | null>(null);
  const [pageLoading, setPageLoading] = useState(true);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [period, setPeriod] = useState("1y");
  const [error, setError] = useState<string | null>(null);
  const [analysisError, setAnalysisError] = useState<string | null>(null);

  /* Step 1: Load portfolio list (fast) */
  const loadPortfolio = useCallback(async () => {
    setPageLoading(true);
    setError(null);
    try {
      const list = await portfolioApi.list();
      if (list.count === 0) {
        setError("No portfolio loaded. Go to Portfolio page to load one.");
        return;
      }
      setPortfolio(list.portfolios[0]);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load portfolio");
    } finally {
      setPageLoading(false);
    }
  }, []);

  /* Step 2: Run risk analysis in background (slow) */
  const loadRisk = useCallback(async (p: PortfolioSummary) => {
    setAnalysisLoading(true);
    setAnalysisError(null);
    try {
      const riskResult = await analysisApi.risk(p.portfolio_id, period);
      setRisk(riskResult);
    } catch (err) {
      setAnalysisError(err instanceof Error ? err.message : "Failed to run risk analysis");
    } finally {
      setAnalysisLoading(false);
    }
  }, [period]);

  useEffect(() => {
    loadPortfolio();
  }, [loadPortfolio]);

  useEffect(() => {
    if (portfolio) loadRisk(portfolio);
  }, [portfolio, loadRisk]);

  const handleRefresh = () => {
    if (portfolio) loadRisk(portfolio);
  };

  if (pageLoading) return <Spinner />;
  if (error) return <EmptyState title="Error" description={error} action={<button onClick={loadPortfolio} className="btn-primary">Retry</button>} />;
  if (!portfolio) return <EmptyState title="No data" description="Load a portfolio first." />;

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <motion.h1 initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} className="text-2xl font-bold text-white">Risk Analysis</motion.h1>
          <p className="text-sm text-neutral-500 mt-1">{portfolio.name} &middot; Period: {period}</p>
        </div>
        <div className="flex items-center gap-3">
          <select value={period} onChange={(e) => setPeriod(e.target.value)} className="bg-neutral-800 border border-neutral-700 text-sm text-neutral-200 rounded-lg px-3 py-1.5">
            <option value="3mo">3 Months</option>
            <option value="6mo">6 Months</option>
            <option value="1y">1 Year</option>
            <option value="2y">2 Years</option>
          </select>
          <button onClick={handleRefresh} disabled={analysisLoading} className="btn-ghost flex items-center gap-2"><RefreshCw className={`h-4 w-4 ${analysisLoading ? "animate-spin" : ""}`} /> Run</button>
        </div>
      </div>

      {/* Analysis loading / error state */}
      {analysisLoading && (
        <Card>
          <div className="flex items-center gap-3 py-6 justify-center">
            <RefreshCw className="h-5 w-5 animate-spin text-accent" />
            <span className="text-neutral-400 text-sm">Running risk analysis... This may take a minute.</span>
          </div>
        </Card>
      )}

      {analysisError && !analysisLoading && (
        <Card>
          <div className="text-center py-6">
            <p className="text-red-400 text-sm mb-2">{analysisError}</p>
            <button onClick={handleRefresh} className="btn-primary text-sm">Retry Analysis</button>
          </div>
        </Card>
      )}

      {risk && !analysisLoading && (() => {
        const pm = risk.portfolio_metrics as Record<string, number>;
        const riskLevel = risk.risk_summary?.risk_level ?? "N/A";
        const assetVolData = risk.asset_metrics.map((a: Record<string, unknown>) => ({ name: a.symbol as string, value: a.volatility as number }));
        const assetSharpeData = risk.asset_metrics.map((a: Record<string, unknown>) => ({ name: a.symbol as string, value: a.sharpe_ratio as number }));

        return (
          <>
            {/* Portfolio metrics */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
              <MetricCard label="Risk Level" value={riskLevel} icon={<ShieldAlert className="h-5 w-5 text-accent" />} />
              <MetricCard label="Volatility" value={formatPercent(pm.volatility)} sub="Annualized" />
              <MetricCard label="VaR (95%)" value={formatPercent(pm.var_historical_95)} sub="Historical" />
              <MetricCard label="Max Drawdown" value={formatPercent(pm.max_drawdown)} />
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <MetricCard label="Sharpe Ratio" value={formatNumber(pm.sharpe_ratio)} />
              <MetricCard label="Sortino Ratio" value={formatNumber(pm.sortino_ratio)} />
              <MetricCard label="CVaR (95%)" value={formatPercent(pm.cvar_95)} sub="Expected Shortfall" />
            </div>

            {/* Charts */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card>
                <SectionHeader title="Asset Volatility" subtitle="Annualized volatility by asset" />
                <MetricsBar data={assetVolData} label="Volatility" />
              </Card>
              <Card>
                <SectionHeader title="Sharpe Ratios" subtitle="Risk-adjusted returns by asset" />
                <MetricsBar data={assetSharpeData} label="Sharpe" />
              </Card>
            </div>

            {/* Findings */}
            <Card>
              <SectionHeader title="Key Findings" />
              {risk.risk_summary?.key_findings?.length ? (
                <ul className="space-y-3">
                  {risk.risk_summary.key_findings.map((f, i) => (
                    <motion.li key={i} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.06 }} className="flex items-start gap-3 text-sm text-neutral-300">
                      <span className="mt-1.5 h-1.5 w-1.5 rounded-full bg-accent flex-shrink-0" />
                      {f}
                    </motion.li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-neutral-500">No key findings.</p>
              )}
            </Card>

            {/* Asset Detail Table */}
            <Card>
              <SectionHeader title="Asset Risk Metrics" subtitle={`${risk.asset_metrics.length} assets analyzed`} />
              <div className="overflow-x-auto">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="text-neutral-500 text-xs uppercase tracking-wider border-b border-neutral-800">
                      <th className="text-left py-3 pr-4">Symbol</th>
                      <th className="text-right py-3 pr-4">Volatility</th>
                      <th className="text-right py-3 pr-4">Sharpe</th>
                      <th className="text-right py-3 pr-4">Sortino</th>
                      <th className="text-right py-3 pr-4">Max DD</th>
                      <th className="text-right py-3 pr-4">VaR 95%</th>
                      <th className="text-right py-3">Avg Return</th>
                    </tr>
                  </thead>
                  <tbody>
                    {risk.asset_metrics.map((a: Record<string, unknown>, i: number) => (
                      <motion.tr key={a.symbol as string} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.03 }} className="border-b border-neutral-800/50 hover:bg-neutral-800/30 transition-colors">
                        <td className="py-3 pr-4 font-medium text-white">{a.symbol as string}</td>
                        <td className="text-right py-3 pr-4 font-mono text-neutral-300">{formatPercent(a.volatility as number)}</td>
                        <td className="text-right py-3 pr-4 font-mono text-neutral-300">{formatNumber(a.sharpe_ratio as number)}</td>
                        <td className="text-right py-3 pr-4 font-mono text-neutral-300">{formatNumber(a.sortino_ratio as number)}</td>
                        <td className="text-right py-3 pr-4 font-mono text-neutral-300">{formatPercent(a.max_drawdown as number)}</td>
                        <td className="text-right py-3 pr-4 font-mono text-neutral-300">{formatPercent(a.var_95 as number)}</td>
                        <td className="text-right py-3 font-mono text-neutral-300">{formatPercent(a.average_return as number)}</td>
                      </motion.tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Card>
          </>
        );
      })()}
    </div>
  );
}
