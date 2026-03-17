"use client";

import React, { useEffect, useState, useCallback } from "react";
import { motion } from "framer-motion";
import { ArrowRightLeft, RefreshCw } from "lucide-react";

import { portfolioApi, analysisApi, type PortfolioSummary, type RebalancingResult } from "@/lib/api";
import { formatCurrency, formatPercent } from "@/lib/utils";
import { Card, MetricCard, Spinner, EmptyState, Badge, SectionHeader } from "@/components/ui";
import { AllocationPie, DriftBar } from "@/components/charts";

export default function RebalancingPage() {
  const [portfolio, setPortfolio] = useState<PortfolioSummary | null>(null);
  const [rebalancing, setRebalancing] = useState<RebalancingResult | null>(null);
  const [pageLoading, setPageLoading] = useState(true);
  const [analysisLoading, setAnalysisLoading] = useState(false);
  const [profile, setProfile] = useState("moderate");
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

  /* Step 2: Run rebalancing in background (slow) */
  const loadRebalancing = useCallback(async (p: PortfolioSummary) => {
    setAnalysisLoading(true);
    setAnalysisError(null);
    try {
      const result = await analysisApi.rebalancing(p.portfolio_id, profile);
      setRebalancing(result);
    } catch (err) {
      setAnalysisError(err instanceof Error ? err.message : "Failed to run rebalancing analysis");
    } finally {
      setAnalysisLoading(false);
    }
  }, [profile]);

  useEffect(() => {
    loadPortfolio();
  }, [loadPortfolio]);

  useEffect(() => {
    if (portfolio) loadRebalancing(portfolio);
  }, [portfolio, loadRebalancing]);

  const handleRefresh = () => {
    if (portfolio) loadRebalancing(portfolio);
  };

  if (pageLoading) return <Spinner />;
  if (error) return <EmptyState title="Error" description={error} action={<button onClick={loadPortfolio} className="btn-primary">Retry</button>} />;
  if (!portfolio) return <EmptyState title="No data" description="Load a portfolio first." />;

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <motion.h1 initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} className="text-2xl font-bold text-white">Rebalancing Advisor</motion.h1>
          <p className="text-sm text-neutral-500 mt-1">{portfolio.name} &middot; {profile} profile</p>
        </div>
        <div className="flex items-center gap-3">
          <select value={profile} onChange={(e) => setProfile(e.target.value)} className="bg-neutral-800 border border-neutral-700 text-sm text-neutral-200 rounded-lg px-3 py-1.5">
            <option value="conservative">Conservative</option>
            <option value="moderate">Moderate</option>
            <option value="aggressive">Aggressive</option>
          </select>
          <button onClick={handleRefresh} disabled={analysisLoading} className="btn-ghost flex items-center gap-2"><RefreshCw className={`h-4 w-4 ${analysisLoading ? "animate-spin" : ""}`} /> Run</button>
        </div>
      </div>

      {/* Analysis loading / error state */}
      {analysisLoading && (
        <Card>
          <div className="flex items-center gap-3 py-6 justify-center">
            <RefreshCw className="h-5 w-5 animate-spin text-accent" />
            <span className="text-neutral-400 text-sm">Running rebalancing analysis... This may take a minute.</span>
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

      {rebalancing && !analysisLoading && (() => {
        const currentPie = Object.entries(rebalancing.current_allocation).map(([name, value]) => ({ name, value }));
        const targetPie = Object.entries(rebalancing.target_allocation).map(([name, value]) => ({ name, value }));
        const driftData = Object.entries(rebalancing.drift_analysis).map(([name, drift]) => ({ name, drift }));

        return (
          <>
            {/* Summary */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <MetricCard label="Portfolio Value" value={formatCurrency(rebalancing.total_value)} icon={<ArrowRightLeft className="h-5 w-5 text-accent" />} />
              <MetricCard label="Needs Rebalancing" value={rebalancing.needs_rebalancing ? "Yes" : "No"} />
              <MetricCard label="Trades Needed" value={String(rebalancing.recommendations.length)} />
            </div>

            {/* Allocation comparison */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              <Card>
                <SectionHeader title="Current Allocation" />
                <AllocationPie data={currentPie} />
              </Card>
              <Card>
                <SectionHeader title="Target Allocation" subtitle={`${rebalancing.risk_profile} profile`} />
                <AllocationPie data={targetPie} />
              </Card>
            </div>

            {/* Drift chart */}
            <Card>
              <SectionHeader title="Allocation Drift" subtitle="Current vs Target (positive = overweight)" />
              <DriftBar data={driftData} />
            </Card>

            {/* Recommendations */}
            <Card>
              <SectionHeader title="Trade Recommendations" subtitle={`${rebalancing.recommendations.length} trades`} />
              {rebalancing.recommendations.length > 0 ? (
                <div className="space-y-3">
                  {rebalancing.recommendations.map((rec: Record<string, unknown>, i: number) => (
                    <motion.div key={i} initial={{ opacity: 0, y: 5 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.06 }} className="flex items-center justify-between p-4 rounded-lg bg-neutral-800/50 border border-neutral-700/50">
                      <div className="flex items-center gap-3">
                        <Badge variant={rec.action === "BUY" ? "success" : "danger"}>{rec.action as string}</Badge>
                        <div>
                          <p className="font-medium text-white">{rec.asset_type as string}</p>
                          <p className="text-xs text-neutral-500">{rec.reason as string}</p>
                        </div>
                      </div>
                      <div className="text-right">
                        <p className="font-mono font-medium text-white">{formatCurrency(rec.trade_value as number)}</p>
                        <p className="text-xs text-neutral-500">
                          {formatPercent(rec.current_pct as number)} &rarr; {formatPercent(rec.target_pct as number)}
                        </p>
                      </div>
                    </motion.div>
                  ))}
                </div>
              ) : (
                <p className="text-sm text-neutral-500">Portfolio is within acceptable drift thresholds. No trades needed.</p>
              )}
            </Card>

            {/* LLM reasoning */}
            {rebalancing.llm_reasoning && (
              <Card>
                <SectionHeader title="AI Analysis" subtitle="Powered by Gemini" />
                <div className="text-sm text-neutral-300 whitespace-pre-wrap leading-relaxed">
                  {rebalancing.llm_reasoning}
                </div>
              </Card>
            )}
          </>
        );
      })()}
    </div>
  );
}
