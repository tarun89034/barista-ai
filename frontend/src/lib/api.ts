/* Barista AI – API client */

const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

const DEFAULT_TIMEOUT_MS = 90_000; // 90 seconds

async function request<T>(path: string, init?: RequestInit & { timeoutMs?: number }): Promise<T> {
  const { timeoutMs = DEFAULT_TIMEOUT_MS, ...fetchInit } = init ?? {};
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);

  try {
    const res = await fetch(`${API_BASE}${path}`, {
      headers: { "Content-Type": "application/json", ...fetchInit?.headers },
      signal: controller.signal,
      ...fetchInit,
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail ?? `API error ${res.status}`);
    }
    return res.json() as Promise<T>;
  } catch (err) {
    if (err instanceof DOMException && err.name === "AbortError") {
      throw new Error(`Request timed out after ${Math.round(timeoutMs / 1000)}s — the server may be processing heavy data. Try again shortly.`);
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}

/* ── Portfolio ──────────────────────────────────────────────────────── */

export interface Asset {
  symbol: string;
  name: string;
  asset_type: string;
  quantity: number;
  purchase_price: number;
  current_price: number | null;
  current_value: number | null;
  sector: string;
}

export interface PortfolioSummary {
  portfolio_id: string;
  name: string;
  asset_count: number;
  total_purchase_value: number;
  total_current_value: number;
  base_currency: string;
  assets: Asset[];
}

export interface PortfolioListResponse {
  portfolios: PortfolioSummary[];
  count: number;
}

export const portfolioApi = {
  list: () => request<PortfolioListResponse>("/api/v1/portfolios"),

  get: (id: string) =>
    request<PortfolioSummary>(`/api/v1/portfolios/${id}`),

  loadSample: () =>
    request<PortfolioSummary>("/api/v1/portfolios/load-sample", {
      method: "POST",
    }),

  upload: async (file: File): Promise<PortfolioSummary> => {
    const form = new FormData();
    form.append("file", file);
    const res = await fetch(`${API_BASE}/api/v1/portfolios/upload`, {
      method: "POST",
      body: form,
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      throw new Error(body.detail ?? `Upload failed ${res.status}`);
    }
    return res.json();
  },

  delete: (id: string) =>
    request<{ status: string }>(`/api/v1/portfolios/${id}`, {
      method: "DELETE",
    }),
};

/* ── Analysis ──────────────────────────────────────────────────────── */

export interface RiskAnalysisResult {
  status: string;
  portfolio_name: string;
  analysis_period: string;
  timestamp: string;
  portfolio_metrics: Record<string, unknown>;
  asset_metrics: Record<string, unknown>[];
  risk_summary: { risk_level?: string; key_findings?: string[] };
}

export interface MarketMonitorResult {
  status: string;
  portfolio_name: string;
  timestamp: string;
  current_prices: Record<string, number>;
  alerts: Record<string, unknown>[];
  alert_count: number;
  market_conditions: Record<string, unknown>;
}

export interface RebalancingResult {
  status: string;
  portfolio_name: string;
  risk_profile: string;
  total_value: number;
  timestamp: string;
  current_allocation: Record<string, number>;
  target_allocation: Record<string, number>;
  drift_analysis: Record<string, number>;
  needs_rebalancing: boolean;
  recommendations: Record<string, unknown>[];
  llm_reasoning: string | null;
}

export interface FullAnalysisResult {
  status: string;
  workflow: string;
  timestamp: string;
  portfolio: Record<string, unknown>;
  risk_analysis: Record<string, unknown>;
  market_monitoring: Record<string, unknown>;
  rebalancing: Record<string, unknown>;
  llm_summary: string | null;
}

export interface LLMInsightResult {
  status: string;
  insight: string | null;
  message: string | null;
}

export const analysisApi = {
  risk: (portfolio_id: string, period = "1y") =>
    request<RiskAnalysisResult>("/api/v1/analysis/risk", {
      method: "POST",
      body: JSON.stringify({ portfolio_id, period }),
    }),

  market: (portfolio_id: string) =>
    request<MarketMonitorResult>("/api/v1/analysis/market", {
      method: "POST",
      body: JSON.stringify({ portfolio_id }),
    }),

  rebalancing: (portfolio_id: string, risk_profile = "moderate") =>
    request<RebalancingResult>("/api/v1/analysis/rebalancing", {
      method: "POST",
      body: JSON.stringify({ portfolio_id, risk_profile }),
    }),

  full: (portfolio_id: string, period = "1y", risk_profile = "moderate") =>
    request<FullAnalysisResult>("/api/v1/analysis/full", {
      method: "POST",
      body: JSON.stringify({ portfolio_id, period, risk_profile }),
    }),

  insights: (portfolio_id: string) =>
    request<LLMInsightResult>("/api/v1/analysis/insights", {
      method: "POST",
      body: JSON.stringify({ portfolio_id, include_risk: true }),
    }),

  riskAdvice: (portfolio_id: string) =>
    request<LLMInsightResult>("/api/v1/analysis/risk-advice", {
      method: "POST",
      body: JSON.stringify({ portfolio_id }),
    }),
};

/* ── Global Market ─────────────────────────────────────────────────── */

export interface GlobalIndexEntry {
  name: string;
  region: string;
  currency: string;
  price: number;
  change: number;
  change_pct: number;
}

export interface GlobalIndicesResult {
  status: string;
  timestamp: string;
  indices: Record<string, GlobalIndexEntry>;
}

/* ── Macro Indicators ──────────────────────────────────────────────── */

export interface MacroObservation {
  date: string;
  value: number;
}

export interface MacroIndicator {
  series_id: string;
  latest_value: number | null;
  latest_date: string | null;
  recent_observations: MacroObservation[];
}

export interface MacroIndicatorsResult {
  status: string;
  timestamp: string;
  indicators: Record<string, MacroIndicator>;
}

/* ── Indian Market ─────────────────────────────────────────────────── */

export interface IndianIndexEntry {
  name: string;
  price: number;
  change: number;
  change_pct: number;
}

export interface IndianStockEntry {
  symbol: string;
  name: string;
  price: number;
  change_pct: number;
  currency: string;
}

export interface IndianMarketResult {
  status: string;
  timestamp: string;
  indices: Record<string, IndianIndexEntry>;
  top_stocks: IndianStockEntry[];
}

/* ── Currency ──────────────────────────────────────────────────────── */

export interface ExchangeRatesResult {
  status: string;
  base: string;
  timestamp: string;
  rates: Record<string, number>;
}

export interface CurrencyConvertResult {
  status: string;
  from: string;
  to: string;
  amount: number;
  converted: number;
  rate: number;
}

export const marketApi = {
  globalIndices: () =>
    request<GlobalIndicesResult>("/api/v1/market/global"),

  macroIndicators: () =>
    request<MacroIndicatorsResult>("/api/v1/market/macro"),

  indianMarket: () =>
    request<IndianMarketResult>("/api/v1/market/indian"),
};

export const currencyApi = {
  rates: (base = "USD") =>
    request<ExchangeRatesResult>(`/api/v1/currency/rates?base=${base}`),

  convert: (from = "USD", to = "INR", amount = 1) =>
    request<CurrencyConvertResult>(
      `/api/v1/currency/convert?from=${from}&to=${to}&amount=${amount}`
    ),
};
