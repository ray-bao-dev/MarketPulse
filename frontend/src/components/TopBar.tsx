import { useEffect, useState } from "react";
import { getMarketStatus, getSyncStatus, type SyncStatus } from "../api/client";

export type AppTab = "market" | "ai";

interface TopBarProps {
  activeTab: AppTab;
  onTabChange: (tab: AppTab) => void;
}

const TABS: { id: AppTab; label: string }[] = [
  { id: "market", label: "Market Data" },
  { id: "ai", label: "AI Analysis" },
];

export function TopBar({ activeTab, onTabChange }: TopBarProps) {
  const [configured, setConfigured] = useState<boolean | null>(null);
  const [syncStatus, setSyncStatus] = useState<SyncStatus | null>(null);

  useEffect(() => {
    getMarketStatus()
      .then((status) => setConfigured(status.configured))
      .catch(() => setConfigured(false));
  }, []);

  useEffect(() => {
    if (!configured) return;

    getSyncStatus()
      .then(setSyncStatus)
      .catch(() => undefined);

    const interval = setInterval(() => {
      getSyncStatus()
        .then(setSyncStatus)
        .catch(() => undefined);
    }, 60_000);

    return () => clearInterval(interval);
  }, [configured]);

  const syncPct =
    syncStatus && syncStatus.sync_jobs_total > 0
      ? Math.round(
          (syncStatus.sync_jobs_complete / syncStatus.sync_jobs_total) * 100,
        )
      : null;

  const showSync =
    syncStatus &&
    !syncStatus.backfill_complete &&
    syncStatus.sync_jobs_total > 0;

  return (
    <header className="top-bar">
      <div className="brand">
        <span className="brand-name">MarketPulse</span>
      </div>

      <nav className="top-bar-nav" aria-label="Main navigation">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            type="button"
            className={`nav-tab${activeTab === tab.id ? " active" : ""}`}
            aria-current={activeTab === tab.id ? "page" : undefined}
            onClick={() => onTabChange(tab.id)}
          >
            {tab.label}
          </button>
        ))}
      </nav>

      <div className="status-cluster">
        {configured !== null && (
          <span
            className={`status-item${configured ? " live" : " offline"}`}
            title={configured ? "Alpaca connected" : "Alpaca not configured"}
          >
            <span className="status-dot" />
            {configured ? "Live" : "Offline"}
          </span>
        )}
        {showSync && syncPct !== null && (
          <span className="status-item syncing" title="Historical data sync">
            <span className="status-dot" />
            Sync {syncPct}%
          </span>
        )}
      </div>
    </header>
  );
}
