import { useMonitoringStore } from './store/monitoringStore';
import { useAegisWebSocket } from './api/websocket';
import { Activity, Briefcase, ShieldAlert, BarChart3, Skull, Server, Play, Square, Power, Settings2 } from 'lucide-react';
import { useState } from 'react';

function App() {
  useAegisWebSocket(['portfolio', 'risk', 'system', 'positions']);
  const { portfolio, risk, system } = useMonitoringStore();
  const [logs, setLogs] = useState<string[]>(["[SYSTEM] Aegis TCC Initialized."]);

  const triggerKillSwitch = async () => {
    if (confirm("DANGER : Voulez-vous vraiment engager le KILL SWITCH (Liquider toutes les positions) ?")) {
      try {
        await fetch('http://127.0.0.1:8000/api/risk/kill-switch', { method: 'POST' });
        setLogs(prev => [...prev, "[RISK] KILL SWITCH ENGAGED! System halted."]);
        alert("KILL SWITCH ENGAGED");
      } catch (e) {
        setLogs(prev => [...prev, "[ERROR] Failed to engage kill switch."]);
      }
    }
  };
  
  const startStrategy = async () => {
    try {
      await fetch('http://127.0.0.1:8000/api/system/strategy/alpha_momentum_v1/start', { method: 'POST' });
      setLogs(prev => [...prev, "[STRATEGY] Command sent: Start alpha_momentum_v1"]);
    } catch (e) {
      setLogs(prev => [...prev, "[ERROR] Failed to connect to API."]);
    }
  };
  
  const stopStrategy = async () => {
    try {
      await fetch('http://127.0.0.1:8000/api/system/strategy/alpha_momentum_v1/stop', { method: 'POST' });
      setLogs(prev => [...prev, "[STRATEGY] Command sent: Stop alpha_momentum_v1"]);
    } catch (e) {
      setLogs(prev => [...prev, "[ERROR] Failed to connect to API."]);
    }
  };

  return (
    <div className="min-h-screen bg-background text-foreground p-6 font-mono flex flex-col gap-6">
      {/* HEADER */}
      <header className="flex justify-between items-center border-b border-gray-800 pb-4">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <Activity className="text-accent" />
          Aegis Trading Control Center
        </h1>
        <div className="flex gap-4 items-center">
          <div className={`px-3 py-1 rounded text-sm flex items-center gap-2 ${system?.broker_status?.connected ? 'bg-green-900 text-green-100' : 'bg-red-900 text-red-100'}`}>
            <Server size={14} />
            {system?.broker_status?.connected ? 'Broker Connected' : 'Broker Disconnected'}
          </div>
          <button 
            onClick={triggerKillSwitch}
            className="px-4 py-1.5 bg-red-600 hover:bg-red-700 text-white font-bold rounded flex items-center gap-2 transition-colors">
            <Skull size={16} />
            KILL SWITCH
          </button>
        </div>
      </header>

      {/* TOP PANELS */}
      <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
        
        {/* Strategy Control */}
        <div className="bg-card p-6 rounded-lg border border-gray-800 shadow-xl">
          <h2 className="text-gray-400 text-sm font-semibold mb-4 flex items-center gap-2">
            <Settings2 size={16} /> STRATEGY CONTROL
          </h2>
          <div className="flex justify-between items-center mb-4">
            <span className="text-sm">ID:</span>
            <span className="font-bold text-accent">{system?.strategy_status?.id || "N/A"}</span>
          </div>
          <div className="flex justify-between items-center mb-4">
            <span className="text-sm">Status:</span>
            <span className="font-bold text-green-400">{system?.strategy_status?.status || "Idle"}</span>
          </div>
          <div className="flex gap-2">
            <button onClick={startStrategy} className="flex-1 bg-gray-800 hover:bg-gray-700 p-2 rounded flex justify-center items-center gap-1 transition-colors">
              <Play size={14} className="text-green-400" /> Start
            </button>
            <button onClick={stopStrategy} className="flex-1 bg-gray-800 hover:bg-gray-700 p-2 rounded flex justify-center items-center gap-1 transition-colors">
              <Square size={14} className="text-red-400" /> Stop
            </button>
          </div>
        </div>

        {/* Broker Status */}
        <div className="bg-card p-6 rounded-lg border border-gray-800 shadow-xl">
          <h2 className="text-gray-400 text-sm font-semibold mb-4 flex items-center gap-2">
            <Power size={16} /> BROKER STATUS
          </h2>
          <div className="space-y-3">
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-400">Gateway:</span>
              <span className="font-bold">{system?.broker_status?.gateway || "-"}</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-400">Latency:</span>
              <span className="font-bold text-yellow-400">{system?.broker_status?.latency_ms || 0} ms</span>
            </div>
            <div className="flex justify-between items-center">
              <span className="text-sm text-gray-400">Services:</span>
              <span className="font-bold">{system?.active_services?.length || 0} active</span>
            </div>
          </div>
        </div>

        {/* Portfolio Card */}
        <div className="bg-card p-6 rounded-lg border border-gray-800 shadow-xl">
          <h2 className="text-gray-400 text-sm font-semibold mb-2 flex items-center gap-2">
            <Briefcase size={16} /> PORTFOLIO EQUITY
          </h2>
          <div className="text-3xl font-bold mt-2">
            ${portfolio ? portfolio.equity.toFixed(2) : "0.00"}
          </div>
          <div className={`text-sm mt-3 ${portfolio && portfolio.total_unrealized_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
            Unrealized PnL: ${portfolio ? portfolio.total_unrealized_pnl.toFixed(2) : "0.00"}
          </div>
        </div>

        {/* Risk Card */}
        <div className="bg-card p-6 rounded-lg border border-gray-800 shadow-xl">
          <h2 className="text-gray-400 text-sm font-semibold mb-2 flex items-center gap-2">
            <ShieldAlert size={16} /> RISK STATUS
          </h2>
          <div className={`text-2xl font-bold mt-2 ${risk?.risk_status === 'NORMAL' ? 'text-green-400' : 'text-yellow-400'}`}>
            {risk ? risk.risk_status : "UNKNOWN"}
          </div>
          <div className="text-sm mt-3 text-gray-500">
            Exposure: {risk ? (risk.global_exposure * 100).toFixed(1) : "0.0"}%
          </div>
        </div>
      </div>

      {/* BOTTOM PANELS */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6 flex-1">
        {/* Positions Card */}
        <div className="bg-card p-6 rounded-lg border border-gray-800 shadow-xl md:col-span-2 flex flex-col">
          <h2 className="text-gray-400 text-sm font-semibold mb-4 flex items-center gap-2">
            <BarChart3 size={16} /> ACTIVE POSITIONS
          </h2>
          <div className="text-2xl font-bold">
            {portfolio ? portfolio.open_positions_count : 0} Open
          </div>
          <div className="mt-4 flex-1 rounded border border-gray-800 bg-black/20 flex items-center justify-center text-gray-600 text-sm">
            Waiting for order executions...
          </div>
        </div>
        
        {/* System Logs */}
        <div className="bg-card p-6 rounded-lg border border-gray-800 shadow-xl flex flex-col">
          <h2 className="text-gray-400 text-sm font-semibold mb-4 flex items-center gap-2">
            <Server size={16} /> SYSTEM LOGS
          </h2>
          <div className="flex-1 bg-[#0a0a0a] border border-gray-800 rounded p-4 overflow-y-auto text-xs text-gray-400 space-y-1 font-mono">
            {logs.map((log, idx) => (
              <div key={idx}>{log}</div>
            ))}
          </div>
        </div>
      </div>
    </div>
  )
}

export default App

