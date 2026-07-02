import { useState } from "react";
import { TopBar, type AppTab } from "./components/TopBar";
import { AiAnalysis } from "./pages/AiAnalysis";
import { Dashboard } from "./pages/Dashboard";

export default function App() {
  const [activeTab, setActiveTab] = useState<AppTab>("market");

  return (
    <div className="app-shell">
      <TopBar activeTab={activeTab} onTabChange={setActiveTab} />
      <div className="app-content">
        {activeTab === "market" ? <Dashboard /> : <AiAnalysis />}
      </div>
    </div>
  );
}
