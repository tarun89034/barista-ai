"use client";

import React, { useEffect, useState, useCallback, useRef } from "react";
import { motion } from "framer-motion";
import { FolderOpen, Upload, Trash2, RefreshCw, Download } from "lucide-react";

import { portfolioApi, type PortfolioSummary } from "@/lib/api";
import { formatCurrency } from "@/lib/utils";
import { Card, Spinner, EmptyState, Badge } from "@/components/ui";

export default function PortfolioPage() {
  const [portfolios, setPortfolios] = useState<PortfolioSummary[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const loadList = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const result = await portfolioApi.list();
      setPortfolios(result.portfolios);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load portfolios");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadList();
  }, [loadList]);

  const handleLoadSample = async () => {
    setUploading(true);
    try {
      await portfolioApi.loadSample();
      await loadList();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load sample");
    } finally {
      setUploading(false);
    }
  };

  const handleUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      await portfolioApi.upload(file);
      await loadList();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Upload failed");
    } finally {
      setUploading(false);
      if (fileRef.current) fileRef.current.value = "";
    }
  };

  const handleDelete = async (id: string) => {
    try {
      await portfolioApi.delete(id);
      setPortfolios((prev) => prev.filter((p) => p.portfolio_id !== id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    }
  };

  return (
    <div className="space-y-8">
      <div className="flex items-center justify-between">
        <div>
          <motion.h1 initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} className="text-2xl font-bold text-white">Portfolio Manager</motion.h1>
          <p className="text-sm text-neutral-500 mt-1">{portfolios.length} portfolio(s) loaded</p>
        </div>
        <div className="flex items-center gap-3">
          <button onClick={handleLoadSample} disabled={uploading} className="btn-secondary flex items-center gap-2">
            <Download className="h-4 w-4" /> Load Sample
          </button>
          <label className="btn-primary flex items-center gap-2 cursor-pointer">
            <Upload className="h-4 w-4" /> Upload CSV
            <input ref={fileRef} type="file" accept=".csv,.xlsx,.xls" className="hidden" onChange={handleUpload} />
          </label>
          <button onClick={loadList} className="btn-ghost"><RefreshCw className="h-4 w-4" /></button>
        </div>
      </div>

      {loading && <Spinner />}
      {error && <div className="text-sm text-danger bg-red-500/10 border border-red-500/20 rounded-lg p-3">{error}</div>}
      {uploading && <div className="text-sm text-accent animate-pulse">Processing portfolio...</div>}

      {!loading && portfolios.length === 0 && (
        <EmptyState
          title="No portfolios"
          description="Upload a CSV file or load the built-in sample portfolio to get started."
          action={<button onClick={handleLoadSample} className="btn-primary">Load Sample Portfolio</button>}
        />
      )}

      {portfolios.map((p, i) => (
        <motion.div key={p.portfolio_id} initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.08 }}>
          <Card>
            <div className="flex items-center justify-between mb-4">
              <div className="flex items-center gap-3">
                <FolderOpen className="h-5 w-5 text-accent" />
                <div>
                  <h3 className="font-semibold text-white">{p.name}</h3>
                  <p className="text-xs text-neutral-500">ID: {p.portfolio_id} &middot; {p.asset_count} assets &middot; {p.base_currency}</p>
                </div>
              </div>
              <div className="flex items-center gap-4">
                <div className="text-right">
                  <p className="text-lg font-semibold text-white">{formatCurrency(p.total_current_value)}</p>
                  <p className="text-xs text-neutral-500">Cost: {formatCurrency(p.total_purchase_value)}</p>
                </div>
                <button onClick={() => handleDelete(p.portfolio_id)} className="p-2 rounded-lg text-neutral-500 hover:text-danger hover:bg-red-500/10 transition-colors" title="Delete portfolio">
                  <Trash2 className="h-4 w-4" />
                </button>
              </div>
            </div>

            {/* Asset summary */}
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="text-neutral-500 text-xs uppercase tracking-wider border-b border-neutral-800">
                    <th className="text-left py-2 pr-4">Symbol</th>
                    <th className="text-left py-2 pr-4">Name</th>
                    <th className="text-left py-2 pr-4">Type</th>
                    <th className="text-right py-2 pr-4">Qty</th>
                    <th className="text-right py-2 pr-4">Current Price</th>
                    <th className="text-right py-2">Value</th>
                  </tr>
                </thead>
                <tbody>
                  {p.assets.map((a) => (
                    <tr key={a.symbol} className="border-b border-neutral-800/50">
                      <td className="py-2 pr-4 font-medium text-white">{a.symbol}</td>
                      <td className="py-2 pr-4 text-neutral-400 text-xs">{a.name}</td>
                      <td className="py-2 pr-4"><Badge>{a.asset_type}</Badge></td>
                      <td className="text-right py-2 pr-4 font-mono text-neutral-300">{a.quantity}</td>
                      <td className="text-right py-2 pr-4 font-mono text-neutral-300">{formatCurrency(a.current_price)}</td>
                      <td className="text-right py-2 font-mono font-medium text-white">{formatCurrency(a.current_value)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>
        </motion.div>
      ))}
    </div>
  );
}
