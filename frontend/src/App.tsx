import { useMonitoringStore } from './store/monitoringStore';
import { useAegisWebSocket } from './api/websocket';
import { Activity, Briefcase, ShieldAlert, BarChart3, TrendingUp, Skull } from 'lucide-react';

function App() {
  useAegisWebSocket(['portfolio', 'risk', 'system', 'positions']);
  const { portfolio, risk } = useMonitoringStore();

  const triggerKillSwitch = async () => {
    if (confirm("DANGER : Voulez-vous vraiment engager le KILL SWITCH (Liquider toutes les positions) ?")) {
      await fetch('http://127.0.0.1:8000/api/risk/kill-switch', { method: 'POST' });
      alert("KILL SWITCH ENGAGED");
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground p-6 font-mono">
      <header className="flex justify-between items-center mb-8 border-b border-gray-800 pb-4">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Activity className="text-accent" />
          Aegis Trading Control Center
        </h1>
        <div className="flex gap-4">
          <div className="px-3 py-1 bg-gray-800 rounded text-sm flex items-center gap-2">
            <span className="w-2 h-2 rounded-full bg-green-500"></span>
            System Online
          </div>
          <button 
            onClick={triggerKillSwitch}
            className="px-4 py-1 bg-red-900 hover:bg-red-700 text-red-100 font-bold rounded flex items-center gap-2 transition-colors">
            <Skull size={16} />
            KILL SWITCH
          </button>
        </div>
      </header>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        
        {/* Portfolio Card */}
        <div className="bg-card p-6 rounded-lg border border-gray-800 shadow-xl">
          <h2 className="text-gray-400 text-sm font-semibold mb-2 flex items-center gap-2">
            <Briefcase size={16} /> PORTFOLIO EQUITY
          </h2>
          <div className="text-3xl font-bold">
            ${portfolio ? portfolio.equity.toFixed(2) : "0.00"}
          </div>
          <div className={`text-sm mt-2 ${portfolio && portfolio.total_unrealized_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            Unrealized PnL: ${portfolio ? portfolio.total_unrealized_pnl.toFixed(2) : "0.00"}
          </div>
        </div>

        {/* Risk Card */}
        <div className="bg-card p-6 rounded-lg border border-gray-800 shadow-xl">
          <h2 className="text-gray-400 text-sm font-semibold mb-2 flex items-center gap-2">
            <ShieldAlert size={16} /> RISK STATUS
          </h2>
          <div className={`text-2xl font-bold ${risk?.risk_status === 'NORMAL' ? 'text-green-400' : 'text-yellow-400'}`}>
            {risk ? risk.risk_status : "UNKNOWN"}
          </div>
          <div className="text-sm mt-2 text-gray-500">
            Exposure: {risk ? (risk.global_exposure * 100).toFixed(1) : "0.0"}%
          </div>
        </div>

        {/* Positions Card */}
        <div className="bg-card p-6 rounded-lg border border-gray-800 shadow-xl md:col-span-2">
          <h2 className="text-gray-400 text-sm font-semibold mb-2 flex items-center gap-2">
            <BarChart3 size={16} /> ACTIVE POSITIONS
          </h2>
          <div className="text-2xl font-bold">
            {portfolio ? portfolio.open_positions_count : 0} Open
          </div>
        </div>

      </div>
    </div>
  )
}

export default App
