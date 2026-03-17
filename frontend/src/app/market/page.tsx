"use client";

import React, { useEffect, useState, useCallback, useRef } from "react";
import { motion } from "framer-motion";
import {
  TrendingUp,
  TrendingDown,
  RefreshCw,
  Bell,
  Wifi,
  WifiOff,
  Globe,
  Landmark,
  IndianRupee,
  BarChart3,
  Activity,
} from "lucide-react";

import {
  portfolioApi,
  analysisApi,
  marketApi,
  type PortfolioSummary,
  type MarketMonitorResult,
  type GlobalIndicesResult,
  type GlobalIndexEntry,
  type MacroIndicatorsResult,
  type MacroIndicator,
  type IndianMarketResult,
  type IndianIndexEntry,
  type IndianStockEntry,
} from "@/lib/api";
import { formatCurrency, formatCompact } from "@/lib/utils";
import { Card, MetricCard, Spinner, EmptyState, Badge, SectionHeader } from "@/components/ui";

/* ── Tab type ──────────────────────────────────────────────────────── */

type Tab = "portfolio" | "global" | "indian" | "macro";

const TABS: { id: Tab; label: string; icon: React.ReactNode }[] = [
  { id: "portfolio", label: "Portfolio", icon: <Activity className="h-4 w-4" /> },
  { id: "global", label: "Global Indices", icon: <Globe className="h-4 w-4" /> },
  { id: "indian", label: "Indian Market", icon: <IndianRupee className="h-4 w-4" /> },
  { id: "macro", label: "Macro Indicators", icon: <Landmark className="h-4 w-4" /> },
];

/* ── Macro label map ───────────────────────────────────────────────── */

const MACRO_LABELS: Record<string, { label: string; unit: string; description: string }> = {
  FEDFUNDS: { label: "Fed Funds Rate", unit: "%", description: "Federal Reserve target interest rate" },
  DGS10: { label: "10-Year Treasury", unit: "%", description: "10-year US Treasury yield" },
  DGS2: { label: "2-Year Treasury", unit: "%", description: "2-year US Treasury yield" },
  CPIAUCSL: { label: "CPI", unit: "index", description: "Consumer Price Index for all urban consumers" },
  UNRATE: { label: "Unemployment Rate", unit: "%", description: "US civilian unemployment rate" },
  GDP: { label: "GDP", unit: "B$", description: "US Gross Domestic Product (billions)" },
  T5YIE: { label: "5Y Inflation Exp.", unit: "%", description: "5-year breakeven inflation rate" },
  VIXCLS: { label: "VIX", unit: "", description: "CBOE Volatility Index (fear gauge)" },
};

export default function MarketPage() {
  const [tab, setTab] = useState<Tab>("portfolio");

  /* Portfolio monitoring state */
  const [portfolio, setPortfolio] = useState<PortfolioSummary | null>(null);
  const [market, setMarket] = useState<MarketMonitorResult | null>(null);
  const [wsConnected, setWsConnected] = useState(false);
  const wsRef = useRef<WebSocket | null>(null);

  /* New market data state */
  const [globalIndices, setGlobalIndices] = useState<GlobalIndicesResult | null>(null);
  const [indianMarket, setIndianMarket] = useState<IndianMarketResult | null>(null);
  const [macroIndicators, setMacroIndicators] = useState<MacroIndicatorsResult | null>(null);

  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  /* ── Data loading ────────────────────────────────────────────────── */

  const loadPortfolioData = useCallback(async () => {
    try {
      const list = await portfolioApi.list();
      if (list.count === 0) return;
      const p = list.portfolios[0];
      setPortfolio(p);
      const result = await analysisApi.market(p.portfolio_id);
      setMarket(result);
    } catch {
      /* silently ignore — portfolio section just won't show data */
    }
  }, []);

  const loadMarketData = useCallback(async (isRefresh = false) => {
    if (isRefresh) setRefreshing(true); else setLoading(true);
    setError(null);
    try {
      const [globalRes, indianRes, macroRes] = await Promise.allSettled([
        marketApi.globalIndices(),
        marketApi.indianMarket(),
        marketApi.macroIndicators(),
      ]);
      if (globalRes.status === "fulfilled") setGlobalIndices(globalRes.value);
      if (indianRes.status === "fulfilled") setIndianMarket(indianRes.value);
      if (macroRes.status === "fulfilled") setMacroIndicators(macroRes.value);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to fetch market data");
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, []);

  /* Load market data and portfolio data independently in parallel */
  useEffect(() => {
    loadMarketData();
    loadPortfolioData();
    return () => wsRef.current?.close();
  }, [loadMarketData, loadPortfolioData]);

  const connectWs = useCallback(() => {
    if (!portfolio) return;
    const wsUrl =
      (process.env.NEXT_PUBLIC_API_URL || `${window.location.protocol === "https:" ? "wss" : "ws"}://${window.location.host}`)
        .replace(/^http/, "ws") + `/api/v1/ws/market/${portfolio.portfolio_id}`;

    const ws = new WebSocket(wsUrl);
    wsRef.current = ws;
    ws.onopen = () => setWsConnected(true);
    ws.onclose = () => setWsConnected(false);
    ws.onerror = () => setWsConnected(false);
    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.type === "market_update") {
          setMarket({
            status: "success",
            portfolio_name: data.portfolio_name,
            timestamp: data.timestamp,
            current_prices: data.current_prices,
            alerts: data.alerts,
            alert_count: data.alert_count,
            market_conditions: data.market_conditions,
          });
        }
      } catch {
        /* ignore parse errors */
      }
    };
  }, [portfolio]);

  useEffect(() => {
    if (portfolio && !wsConnected) connectWs();
    return () => wsRef.current?.close();
  }, [portfolio, connectWs, wsConnected]);

  /* ── Derived data ────────────────────────────────────────────────── */

  const prices = market?.current_prices ?? {};
  const priceEntries = Object.entries(prices);
  const conditions = (market?.market_conditions ?? {}) as Record<string, unknown>;
  const gainers = (conditions.gainers as { symbol: string; change: number }[]) ?? [];
  const losers = (conditions.losers as { symbol: string; change: number }[]) ?? [];

  const indexEntries = globalIndices?.indices
    ? (Object.entries(globalIndices.indices) as [string, GlobalIndexEntry][])
    : [];

  const indianIndices = indianMarket?.indices
    ? (Object.entries(indianMarket.indices) as [string, IndianIndexEntry][])
    : [];
  const indianStocks = indianMarket?.top_stocks ?? [];

  const macroEntries = macroIndicators?.indicators
    ? (Object.entries(macroIndicators.indicators) as [string, MacroIndicator][])
    : [];

  if (loading && !globalIndices && !indianMarket && !macroIndicators)
    return <Spinner />;
  if (error && !market && !globalIndices)
    return <EmptyState title="Error" description={error} action={<button onClick={() => loadMarketData()} className="btn-primary">Retry</button>} />;

  return (
    <div className="space-y-8">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <motion.h1 initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} className="text-2xl font-bold text-white">
            Market Monitor
          </motion.h1>
          <p className="text-sm text-neutral-500 mt-1">
            Real-time market data &middot; Global &amp; Indian markets &middot; Macro indicators
          </p>
        </div>
        <div className="flex items-center gap-3">
          {portfolio && (
            <Badge variant={wsConnected ? "success" : "default"}>
              {wsConnected ? <><Wifi className="h-3 w-3 mr-1" /> Live</> : <><WifiOff className="h-3 w-3 mr-1" /> Offline</>}
            </Badge>
          )}
          <button onClick={() => { loadMarketData(true); loadPortfolioData(); }} className="btn-ghost flex items-center gap-2">
            <RefreshCw className={`h-4 w-4 ${refreshing ? "animate-spin" : ""}`} /> Refresh
          </button>
        </div>
      </div>

      {/* Tab Bar */}
      <div className="flex gap-1 p-1 bg-neutral-900/50 rounded-lg border border-neutral-800/50 w-fit">
        {TABS.map((t) => (
          <button
            key={t.id}
            onClick={() => setTab(t.id)}
            className={`flex items-center gap-2 px-4 py-2 rounded-md text-sm font-medium transition-all ${
              tab === t.id
                ? "bg-neutral-800 text-white shadow-sm"
                : "text-neutral-500 hover:text-neutral-300 hover:bg-neutral-800/50"
            }`}
          >
            {t.icon}
            {t.label}
          </button>
        ))}
      </div>

      {/* ── PORTFOLIO TAB ──────────────────────────────────────────── */}
      {tab === "portfolio" && (
        <>
          {!portfolio || !market ? (
            <EmptyState title="No portfolio loaded" description="Load a portfolio from the Portfolio page to see live market monitoring." />
          ) : (
            <>
              {/* Summary Metrics */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
                <MetricCard label="Assets Tracked" value={String(priceEntries.length)} icon={<TrendingUp className="h-5 w-5 text-accent" />} />
                <MetricCard label="Alerts" value={String(market.alert_count)} icon={<Bell className="h-5 w-5 text-accent" />} />
                <MetricCard label="Last Update" value={new Date(market.timestamp).toLocaleTimeString()} sub={new Date(market.timestamp).toLocaleDateString()} />
              </div>

              {/* Gainers + Losers */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
                <Card>
                  <SectionHeader title="Top Gainers" />
                  {gainers.length > 0 ? (
                    <div className="space-y-2">
                      {gainers.map((g, i) => (
                        <motion.div key={g.symbol} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.05 }} className="flex items-center justify-between py-2 border-b border-neutral-800/50">
                          <span className="font-medium text-white">{g.symbol}</span>
                          <span className="text-success font-mono text-sm">+{(g.change * 100).toFixed(2)}%</span>
                        </motion.div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-neutral-500">No gainers detected yet.</p>
                  )}
                </Card>
                <Card>
                  <SectionHeader title="Top Losers" />
                  {losers.length > 0 ? (
                    <div className="space-y-2">
                      {losers.map((l, i) => (
                        <motion.div key={l.symbol} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.05 }} className="flex items-center justify-between py-2 border-b border-neutral-800/50">
                          <span className="font-medium text-white">{l.symbol}</span>
                          <span className="text-danger font-mono text-sm">{(l.change * 100).toFixed(2)}%</span>
                        </motion.div>
                      ))}
                    </div>
                  ) : (
                    <p className="text-sm text-neutral-500">No losers detected yet.</p>
                  )}
                </Card>
              </div>

              {/* Current Prices Table */}
              <Card>
                <SectionHeader title="Current Prices" subtitle="Real-time market data" />
                <div className="overflow-x-auto">
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-neutral-500 text-xs uppercase tracking-wider border-b border-neutral-800">
                        <th className="text-left py-3 pr-4">Symbol</th>
                        <th className="text-right py-3">Price</th>
                      </tr>
                    </thead>
                    <tbody>
                      {priceEntries.map(([symbol, price], i) => (
                        <motion.tr key={symbol} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.02 }} className="border-b border-neutral-800/50 hover:bg-neutral-800/30 transition-colors">
                          <td className="py-3 pr-4 font-medium text-white">{symbol}</td>
                          <td className="text-right py-3 font-mono text-neutral-300">{formatCurrency(price)}</td>
                        </motion.tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </Card>

              {/* Alerts */}
              {market.alerts.length > 0 && (
                <Card>
                  <SectionHeader title="Alerts" subtitle={`${market.alert_count} alerts generated`} />
                  <div className="space-y-3">
                    {market.alerts.map((alert: Record<string, unknown>, i: number) => (
                      <motion.div key={i} initial={{ opacity: 0, x: -5 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.05 }} className="flex items-start gap-3 p-3 rounded-lg bg-neutral-800/50 border border-neutral-700/50">
                        <Bell className="h-4 w-4 text-warning mt-0.5 flex-shrink-0" />
                        <div>
                          <p className="text-sm text-neutral-200">{alert.message as string}</p>
                          <p className="text-xs text-neutral-500 mt-1">{alert.severity as string} &middot; {alert.symbol as string}</p>
                        </div>
                      </motion.div>
                    ))}
                  </div>
                </Card>
              )}
            </>
          )}
        </>
      )}

      {/* ── GLOBAL INDICES TAB ─────────────────────────────────────── */}
      {tab === "global" && (
        <>
          {indexEntries.length === 0 ? (
            <EmptyState title="No global data" description="Global indices data could not be loaded. Try refreshing." action={<button onClick={() => loadMarketData()} className="btn-primary">Retry</button>} />
          ) : (
            <>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                {indexEntries.map(([symbol, idx], i) => (
                  <motion.div
                    key={symbol}
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: i * 0.04 }}
                  >
                    <Card className="relative overflow-hidden">
                      <div className="flex items-start justify-between mb-3">
                        <div className="min-w-0 flex-1">
                          <p className="text-xs text-neutral-500 font-medium uppercase tracking-wider truncate">{idx.name}</p>
                          <p className="text-[10px] text-neutral-600 mt-0.5">{symbol} &middot; {idx.region}</p>
                        </div>
                        <Badge variant={idx.change_pct >= 0 ? "success" : "danger"}>
                          {idx.currency}
                        </Badge>
                      </div>
                      <div className="flex items-end justify-between">
                        <p className="text-xl font-mono font-semibold text-white">{formatCompact(idx.price)}</p>
                        <div className={`flex items-center gap-1 text-sm font-mono ${idx.change_pct >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                          {idx.change_pct >= 0 ? <TrendingUp className="h-4 w-4" /> : <TrendingDown className="h-4 w-4" />}
                          <span>{idx.change_pct >= 0 ? "+" : ""}{idx.change_pct.toFixed(2)}%</span>
                        </div>
                      </div>
                      {/* Subtle colored bar at bottom */}
                      <div className={`absolute bottom-0 left-0 right-0 h-0.5 ${idx.change_pct >= 0 ? "bg-emerald-500/40" : "bg-red-500/40"}`} />
                    </Card>
                  </motion.div>
                ))}
              </div>
              {globalIndices?.timestamp && (
                <p className="text-xs text-neutral-600 text-right">
                  Last updated: {new Date(globalIndices.timestamp).toLocaleString()}
                </p>
              )}
            </>
          )}
        </>
      )}

      {/* ── INDIAN MARKET TAB ──────────────────────────────────────── */}
      {tab === "indian" && (
        <>
          {indianIndices.length === 0 && indianStocks.length === 0 ? (
            <EmptyState title="No Indian market data" description="Indian market data could not be loaded. Try refreshing." action={<button onClick={() => loadMarketData()} className="btn-primary">Retry</button>} />
          ) : (
            <>
              {/* Indian Indices */}
              {indianIndices.length > 0 && (
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {indianIndices.map(([symbol, idx], i) => (
                    <motion.div key={symbol} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.06 }}>
                      <Card className="relative overflow-hidden">
                        <div className="flex items-center gap-3 mb-3">
                          <div className="p-2 rounded-lg bg-neutral-800">
                            <IndianRupee className="h-5 w-5 text-accent" />
                          </div>
                          <div>
                            <p className="text-sm font-medium text-white">{idx.name}</p>
                            <p className="text-xs text-neutral-500">{symbol}</p>
                          </div>
                        </div>
                        <div className="flex items-end justify-between">
                          <p className="text-2xl font-mono font-semibold text-white">{formatCompact(idx.price)}</p>
                          <div className={`flex items-center gap-1 font-mono ${idx.change_pct >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                            {idx.change_pct >= 0 ? <TrendingUp className="h-5 w-5" /> : <TrendingDown className="h-5 w-5" />}
                            <span className="text-lg font-semibold">{idx.change_pct >= 0 ? "+" : ""}{idx.change_pct.toFixed(2)}%</span>
                          </div>
                        </div>
                        <div className={`absolute bottom-0 left-0 right-0 h-1 ${idx.change_pct >= 0 ? "bg-emerald-500/30" : "bg-red-500/30"}`} />
                      </Card>
                    </motion.div>
                  ))}
                </div>
              )}

              {/* Top NSE Stocks */}
              {indianStocks.length > 0 && (
                <Card>
                  <SectionHeader title="Top NSE Stocks" subtitle={`${indianStocks.length} stocks`} />
                  <div className="overflow-x-auto">
                    <table className="w-full text-sm">
                      <thead>
                        <tr className="text-neutral-500 text-xs uppercase tracking-wider border-b border-neutral-800">
                          <th className="text-left py-3 pr-4">#</th>
                          <th className="text-left py-3 pr-4">Symbol</th>
                          <th className="text-left py-3 pr-4">Name</th>
                          <th className="text-right py-3 pr-4">Price</th>
                          <th className="text-right py-3">Change</th>
                        </tr>
                      </thead>
                      <tbody>
                        {indianStocks.map((s: IndianStockEntry, i: number) => (
                          <motion.tr key={s.symbol} initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: i * 0.03 }} className="border-b border-neutral-800/50 hover:bg-neutral-800/30 transition-colors">
                            <td className="py-3 pr-4 text-neutral-500 font-mono text-xs">{i + 1}</td>
                            <td className="py-3 pr-4 font-medium text-white">{s.symbol}</td>
                            <td className="py-3 pr-4 text-neutral-400">{s.name}</td>
                            <td className="text-right py-3 pr-4 font-mono text-neutral-300">{formatCurrency(s.price, s.currency)}</td>
                            <td className={`text-right py-3 font-mono font-medium ${s.change_pct >= 0 ? "text-emerald-400" : "text-red-400"}`}>
                              {s.change_pct >= 0 ? "+" : ""}{s.change_pct.toFixed(2)}%
                            </td>
                          </motion.tr>
                        ))}
                      </tbody>
                    </table>
                  </div>
                </Card>
              )}

              {indianMarket?.timestamp && (
                <p className="text-xs text-neutral-600 text-right">
                  Last updated: {new Date(indianMarket.timestamp).toLocaleString()}
                </p>
              )}
            </>
          )}
        </>
      )}

      {/* ── MACRO INDICATORS TAB ───────────────────────────────────── */}
      {tab === "macro" && (
        <>
          {macroEntries.length === 0 ? (
            <EmptyState title="No macro data" description="FRED economic indicators could not be loaded. Try refreshing." action={<button onClick={() => loadMarketData()} className="btn-primary">Retry</button>} />
          ) : (
            <>
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
                {macroEntries.map(([seriesId, ind], i) => {
                  const meta = MACRO_LABELS[seriesId] ?? { label: seriesId, unit: "", description: "" };
                  const val = ind.latest_value;
                  return (
                    <motion.div key={seriesId} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.05 }}>
                      <Card className="h-full">
                        <div className="flex items-start gap-3 mb-3">
                          <div className="p-2 rounded-lg bg-neutral-800">
                            <BarChart3 className="h-4 w-4 text-accent" />
                          </div>
                          <div className="min-w-0 flex-1">
                            <p className="text-sm font-medium text-white truncate">{meta.label}</p>
                            <p className="text-[10px] text-neutral-600 leading-tight">{meta.description}</p>
                          </div>
                        </div>
                        <div className="flex items-end justify-between">
                          <div>
                            <p className="text-2xl font-mono font-semibold text-white">
                              {val != null ? val.toFixed(2) : "N/A"}
                            </p>
                            {meta.unit && <p className="text-xs text-neutral-500">{meta.unit}</p>}
                          </div>
                          {ind.latest_date && (
                            <p className="text-[10px] text-neutral-600">{ind.latest_date}</p>
                          )}
                        </div>

                        {/* Mini sparkline of recent observations */}
                        {ind.recent_observations.length > 1 && (
                          <div className="mt-3 flex items-end gap-px h-8">
                            {(() => {
                              const obs = ind.recent_observations.slice(-12);
                              const vals = obs.map((o) => o.value);
                              const min = Math.min(...vals);
                              const max = Math.max(...vals);
                              const range = max - min || 1;
                              return obs.map((o, j) => {
                                const h = ((o.value - min) / range) * 100;
                                const isLast = j === obs.length - 1;
                                return (
                                  <div
                                    key={j}
                                    className={`flex-1 rounded-t-sm ${isLast ? "bg-accent" : "bg-neutral-700"}`}
                                    style={{ height: `${Math.max(h, 8)}%` }}
                                    title={`${o.date}: ${o.value}`}
                                  />
                                );
                              });
                            })()}
                          </div>
                        )}
                      </Card>
                    </motion.div>
                  );
                })}
              </div>

              {/* Spread indicators */}
              {(() => {
                const dgs10 = macroIndicators?.indicators?.DGS10?.latest_value;
                const dgs2 = macroIndicators?.indicators?.DGS2?.latest_value;
                const fedfunds = macroIndicators?.indicators?.FEDFUNDS?.latest_value;
                if (dgs10 == null || dgs2 == null) return null;
                const spread = dgs10 - dgs2;
                const inverted = spread < 0;
                return (
                  <Card>
                    <SectionHeader title="Yield Curve" subtitle="Key spreads and signals" />
                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
                      <div>
                        <p className="text-xs text-neutral-500 uppercase tracking-wider mb-1">10Y-2Y Spread</p>
                        <p className={`text-xl font-mono font-semibold ${inverted ? "text-red-400" : "text-emerald-400"}`}>
                          {spread.toFixed(2)} bps
                        </p>
                        <Badge variant={inverted ? "danger" : "success"}>
                          {inverted ? "Inverted" : "Normal"}
                        </Badge>
                      </div>
                      <div>
                        <p className="text-xs text-neutral-500 uppercase tracking-wider mb-1">10-Year Yield</p>
                        <p className="text-xl font-mono font-semibold text-white">{dgs10.toFixed(2)}%</p>
                      </div>
                      <div>
                        <p className="text-xs text-neutral-500 uppercase tracking-wider mb-1">Fed Funds Rate</p>
                        <p className="text-xl font-mono font-semibold text-white">{fedfunds != null ? `${fedfunds.toFixed(2)}%` : "N/A"}</p>
                      </div>
                    </div>
                  </Card>
                );
              })()}

              {macroIndicators?.timestamp && (
                <p className="text-xs text-neutral-600 text-right">
                  Last updated: {new Date(macroIndicators.timestamp).toLocaleString()}
                </p>
              )}
            </>
          )}
        </>
      )}
    </div>
  );
}
