import { useState, useEffect, useRef } from 'react';
import { useMonitoringStore } from './store/monitoringStore';
import { useAegisWebSocket } from './api/websocket';
import { Activity, Play, Square, Settings, ShieldAlert, LineChart, Brain, Cpu, BookOpen, ShieldCheck, Briefcase, BarChart3, Skull, Server, LayoutDashboard, List, X } from 'lucide-react';
import { ValidationTab } from './components/tabs/ValidationTab';
import { CapitalTab } from './components/tabs/CapitalTab';
import { CouncilTab } from './components/tabs/CouncilTab';
import { KnowledgeTab } from './components/tabs/KnowledgeTab';
import { createChart, ColorType, AreaSeries } from 'lightweight-charts';
import type { UTCTimestamp } from 'lightweight-charts';

// --- Components ---

const Modal = ({ isOpen, onClose, title, content }: { isOpen: boolean, onClose: () => void, title: string, content: React.ReactNode }) => {
  if (!isOpen) return null;
  return (
    <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50">
      <div className="bg-card border border-gray-800 p-6 rounded-lg shadow-2xl max-w-md w-full">
        <div className="flex justify-between items-center mb-4">
          <h3 className="text-lg font-bold text-white">{title}</h3>
          <button onClick={onClose} className="text-gray-400 hover:text-white"><X size={20} /></button>
        </div>
        <div className="text-gray-300 font-mono text-sm">
          {content}
        </div>
        <div className="mt-6 flex justify-end">
          <button onClick={onClose} className="px-4 py-2 bg-gray-800 hover:bg-gray-700 text-white rounded">Fermer</button>
        </div>
      </div>
    </div>
  );
};

const EquityChart = () => {
  const chartContainerRef = useRef<HTMLDivElement>(null);
  
  useEffect(() => {
    if (chartContainerRef.current) {
      const chart = createChart(chartContainerRef.current, {
        layout: { background: { type: ColorType.Solid, color: 'transparent' }, textColor: '#9ca3af' },
        grid: { vertLines: { color: '#1f2937' }, horzLines: { color: '#1f2937' } },
        width: chartContainerRef.current.clientWidth,
        height: 300,
      });
      const areaSeries = chart.addSeries(AreaSeries, {
        lineColor: '#22c55e', topColor: '#22c55e40', bottomColor: '#22c55e00',
      });
      
      // Fetch history data
      fetch('http://127.0.0.1:8000/api/portfolio/history?range=1d')
        .then(res => res.json())
        .then(data => {
          if (Array.isArray(data) && data.length > 0) {
            const formattedData = data.map((d: any) => ({
              time: (new Date(d.timestamp).getTime() / 1000) as UTCTimestamp,
              value: d.equity
            }));
            // Data must be sorted by time ascending
            formattedData.sort((a: any, b: any) => a.time - b.time);
            
            // Deduplicate exact timestamps if any
            const uniqueData = [];
            let lastTime = 0;
            for (const p of formattedData) {
               if (p.time > lastTime) {
                   uniqueData.push(p);
                   lastTime = p.time;
               }
            }
            if (uniqueData.length > 0) {
              areaSeries.setData(uniqueData);
            }
          }
        }).catch(err => console.error("Failed to load equity history:", err));

      const handleResize = () => {
        if (chartContainerRef.current) {
          chart.applyOptions({ width: chartContainerRef.current.clientWidth });
        }
      };
      window.addEventListener('resize', handleResize);
      return () => {
        window.removeEventListener('resize', handleResize);
        chart.remove();
      };
    }
  }, []);

  return <div ref={chartContainerRef} className="w-full h-[300px]" />;
};


// --- Main App ---

function App() {
  useAegisWebSocket(['portfolio', 'risk', 'system', 'positions', 'trades']);
  const { portfolio, risk, system, positions } = useMonitoringStore();
  const [logs, setLogs] = useState<string[]>(["[SYSTEM] Aegis TCC Initialized."]);
  const [activeTab, setActiveTab] = useState<string>('trading');
  
  // Modal State
  const [modalState, setModalState] = useState<{isOpen: boolean, title: string, content: React.ReactNode}>({ isOpen: false, title: '', content: null });

  // Trades state for Journal
  const [trades, setTrades] = useState<any[]>([]);

  useEffect(() => {
    if (activeTab === 'journal') {
      fetch('http://127.0.0.1:8000/api/trades')
        .then(res => res.json())
        .then(data => setTrades(data))
        .catch(err => console.error("Failed to fetch trades", err));
    }
  }, [activeTab]);

  const triggerKillSwitch = async () => {
    setModalState({ isOpen: true, title: "KILL SWITCH", content: "Demande de confirmation..." });
    if (confirm("DANGER : Voulez-vous vraiment engager le KILL SWITCH (Liquider toutes les positions) ?")) {
      try {
        const res = await fetch('http://127.0.0.1:8000/api/risk/kill-switch', { method: 'POST' });
        const data = await res.json();
        setLogs(prev => [...prev, "[RISK] KILL SWITCH ENGAGED! System halted."]);
        setModalState({
          isOpen: true,
          title: "KILL SWITCH ACTIVATED",
          content: <div>{data.message || "Toutes les positions ont été liquidées avec succès."}</div>
        });
      } catch (e) {
        setLogs(prev => [...prev, "[ERROR] Failed to engage kill switch."]);
        setModalState({ isOpen: true, title: "ERREUR", content: "Impossible d'engager le kill switch." });
      }
    } else {
        setModalState({ isOpen: false, title: "", content: null });
    }
  };
  
  const startStrategy = async () => {
    try {
      const strategyId = system?.strategy_status?.id || "alpha_momentum_v1";
      const res = await fetch(`http://127.0.0.1:8000/api/system/strategy/${strategyId}/start`, { method: 'POST' });
      const data = await res.json();
      setLogs(prev => [...prev, `[STRATEGY] Command sent: Start ${strategyId}`]);
      setModalState({ isOpen: true, title: "Stratégie Démarrée", content: data.message || `La stratégie ${strategyId} a été démarrée.` });
    } catch (e) {
      setLogs(prev => [...prev, "[ERROR] Failed to connect to API."]);
    }
  };
  
  const stopStrategy = async () => {
    try {
      const strategyId = system?.strategy_status?.id || "alpha_momentum_v1";
      const res = await fetch(`http://127.0.0.1:8000/api/system/strategy/${strategyId}/stop`, { method: 'POST' });
      const data = await res.json();
      setLogs(prev => [...prev, `[STRATEGY] Command sent: Stop ${strategyId}`]);
      setModalState({ isOpen: true, title: "Stratégie Arrêtée", content: data.message || `La stratégie ${strategyId} a été arrêtée.` });
    } catch (e) {
      setLogs(prev => [...prev, "[ERROR] Failed to connect to API."]);
    }
  };

  const closePosition = async (symbol: string) => {
    try {
      const res = await fetch(`http://127.0.0.1:8000/api/positions/${symbol}/close`, { method: 'POST' });
      const data = await res.json();
      setModalState({ isOpen: true, title: "Position Clôturée", content: `Ordre de clôture envoyé pour ${symbol} (ID: ${data.order_id})` });
    } catch (e) {
      setModalState({ isOpen: true, title: "Erreur", content: `Impossible de clôturer ${symbol}` });
    }
  };

  const exportCSV = () => {
    if (trades.length === 0) return;
    const header = "ID,Symbol,Side,Entry,Exit,Volume,PnL($),PnL(%),Duration(s),Mode\n";
    const rows = trades.map(t => 
      `${t.trade_id},${t.symbol.name},${t.side},${t.entry_price},${t.exit_price},${t.volume},${t.realized_pnl_amount},${t.realized_pnl_percent},${t.duration_seconds},${t.mode}`
    ).join("\n");
    const blob = new Blob([header + rows], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.setAttribute('hidden', '');
    a.setAttribute('href', url);
    a.setAttribute('download', 'trades.csv');
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
  };

  const mode = system?.current_mode || "PAPER";
  const modeColor = mode === "LIVE" ? "bg-red-600 text-white animate-pulse" : "bg-green-600 text-white";

  const renderTabNav = () => (
    <nav className="flex space-x-1 border-b border-gray-800 mb-6 overflow-x-auto pb-2">
      {[
        { id: 'trading', label: 'Trading', icon: Activity },
        { id: 'performance', label: 'Performance', icon: LineChart },
        { id: 'council', label: 'Council', icon: Cpu },
        { id: 'knowledge', label: 'Knowledge', icon: BookOpen },
        { id: 'risk', label: 'Risque & Capital', icon: ShieldCheck },
        { id: 'data', label: 'Données & Validation', icon: Brain },
        { id: 'journal', label: 'Journal', icon: List },
      ].map(tab => (
        <button
          key={tab.id}
          onClick={() => setActiveTab(tab.id)}
          className={`flex items-center gap-2 px-4 py-2 rounded-t font-semibold text-sm transition-colors whitespace-nowrap
            ${activeTab === tab.id ? 'bg-gray-800 text-white border-b-2 border-accent' : 'text-gray-400 hover:text-gray-200 hover:bg-gray-800/50'}`}
        >
          <tab.icon size={16} />
          {tab.label}
        </button>
      ))}
    </nav>
  );

  return (
    <div className="min-h-screen bg-background text-foreground p-6 font-mono flex flex-col gap-6">
      <Modal isOpen={modalState.isOpen} onClose={() => setModalState({ ...modalState, isOpen: false })} title={modalState.title} content={modalState.content} />
      
      {/* HEADER */}
      <header className="flex justify-between items-center border-b border-gray-800 pb-4">
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <LayoutDashboard className="text-accent" />
          Aegis Quant OS
        </h1>
        <div className="flex gap-4 items-center">
          <div className={`px-3 py-1 rounded text-sm font-bold flex items-center gap-2 ${modeColor}`}>
            {mode}
          </div>
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

      {renderTabNav()}

      {/* TRADING TAB */}
      {activeTab === 'trading' && (
        <div className="flex flex-col gap-6 flex-1">
          <div className="grid grid-grid-cols-1 md:grid-cols-4 gap-6">
            {/* Strategy Control */}
            <div className="bg-card p-6 rounded-lg border border-gray-800 shadow-xl">
              <h2 className="text-gray-400 text-sm font-semibold mb-4 flex items-center gap-2">
                <Settings size={16} /> STRATEGY CONTROL
              </h2>
              <div className="flex justify-between items-center mb-4">
                <span className="text-sm">ID:</span>
                <span className="font-bold text-accent truncate max-w-[120px]">{system?.strategy_status?.id || "N/A"}</span>
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
                <Server size={16} /> BROKER STATUS
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

          <div className="grid grid-cols-1 md:grid-cols-3 gap-6 flex-1">
            {/* Positions Table */}
            <div className="bg-card p-6 rounded-lg border border-gray-800 shadow-xl md:col-span-2 flex flex-col">
              <h2 className="text-gray-400 text-sm font-semibold mb-4 flex items-center gap-2">
                <BarChart3 size={16} /> ACTIVE POSITIONS ({portfolio?.open_positions_count || 0})
              </h2>
              <div className="overflow-x-auto flex-1">
                <table className="w-full text-sm text-left">
                  <thead className="text-xs text-gray-400 uppercase bg-gray-800/50">
                    <tr>
                      <th className="px-4 py-2 rounded-tl">Symbol</th>
                      <th className="px-4 py-2">Side</th>
                      <th className="px-4 py-2">Size</th>
                      <th className="px-4 py-2">Entry</th>
                      <th className="px-4 py-2">PnL</th>
                      <th className="px-4 py-2 rounded-tr">Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {Object.values(positions || {}).map((pos: any) => (
                      <tr key={pos.symbol} className="border-b border-gray-800 hover:bg-gray-800/20">
                        <td className="px-4 py-2 font-bold">{pos.symbol}</td>
                        <td className={`px-4 py-2 font-bold ${pos.side === 'LONG' ? 'text-green-400' : 'text-red-400'}`}>{pos.side}</td>
                        <td className="px-4 py-2">{pos.quantity}</td>
                        <td className="px-4 py-2">${Number(pos.entry_price).toFixed(5)}</td>
                        <td className={`px-4 py-2 ${pos.unrealized_pnl >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                          ${Number(pos.unrealized_pnl).toFixed(2)}
                        </td>
                        <td className="px-4 py-2">
                          <button onClick={() => closePosition(pos.symbol)} className="px-3 py-1 bg-red-600 hover:bg-red-700 text-white rounded text-xs font-bold transition-colors">
                            CLOSE
                          </button>
                        </td>
                      </tr>
                    ))}
                    {(!positions || Object.keys(positions).length === 0) && (
                      <tr>
                        <td colSpan={6} className="px-4 py-8 text-center text-gray-500">
                          Aucune position ouverte.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
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
      )}

      {/* PERFORMANCE TAB */}
      {activeTab === 'performance' && (
        <div className="flex flex-col gap-6 flex-1">
          <div className="bg-card p-6 rounded-lg border border-gray-800 shadow-xl">
             <h2 className="text-gray-400 text-sm font-semibold mb-4 flex items-center gap-2">
                <LineChart size={16} /> EQUITY CURVE
             </h2>
             <EquityChart />
          </div>
          <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
             <div className="bg-card p-6 rounded-lg border border-gray-800 shadow-xl">
               <h2 className="text-gray-400 text-sm font-semibold mb-4">MÉTRIQUES CLÉS</h2>
               <div className="space-y-4 text-sm">
                 <div className="flex justify-between border-b border-gray-800 pb-2">
                    <span className="text-gray-400">Total Realized PnL:</span>
                    <span className={`font-bold ${Number(portfolio?.total_realized_pnl || 0) >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                      ${Number(portfolio?.total_realized_pnl || 0).toFixed(2)}
                    </span>
                 </div>
                 {/* Placeholders for performance stats that will come from PerformanceSnapshot */}
                 <div className="flex justify-between border-b border-gray-800 pb-2">
                    <span className="text-gray-400">Win Rate:</span>
                    <span className="font-bold text-gray-200">En attente (Data)</span>
                 </div>
                 <div className="flex justify-between border-b border-gray-800 pb-2">
                    <span className="text-gray-400">Max Drawdown:</span>
                    <span className="font-bold text-gray-200">En attente (Data)</span>
                 </div>
               </div>
             </div>
             <div className="bg-card p-6 rounded-lg border border-gray-800 shadow-xl flex flex-col justify-center">
               <h2 className="text-gray-400 text-sm font-semibold mb-4">OBJECTIF VOLUME (100-200/jour)</h2>
               <div className="w-full bg-gray-800 rounded-full h-4 mb-2">
                 <div className="bg-accent h-4 rounded-full" style={{ width: `${Math.min((trades.length / 100) * 100, 100)}%` }}></div>
               </div>
               <div className="text-right text-xs text-gray-400">{trades.length} trades enregistrés</div>
             </div>
          </div>
        </div>
      )}

      {/* JOURNAL TAB */}
      {activeTab === 'journal' && (
        <div className="bg-card p-6 rounded-lg border border-gray-800 shadow-xl flex-1 flex flex-col">
           <div className="flex justify-between items-center mb-4">
             <h2 className="text-gray-400 text-sm font-semibold flex items-center gap-2">
                <List size={16} /> HISTORIQUE DES TRADES
             </h2>
             <button onClick={exportCSV} className="px-3 py-1 bg-gray-800 hover:bg-gray-700 text-white rounded text-xs transition-colors">
               Exporter CSV
             </button>
           </div>
           <div className="overflow-x-auto flex-1 border border-gray-800 rounded">
             <table className="w-full text-sm text-left">
               <thead className="text-xs text-gray-400 uppercase bg-gray-800/50">
                 <tr>
                   <th className="px-4 py-2">ID</th>
                   <th className="px-4 py-2">Symbol</th>
                   <th className="px-4 py-2">Side</th>
                   <th className="px-4 py-2">Entry</th>
                   <th className="px-4 py-2">Exit</th>
                   <th className="px-4 py-2">Volume</th>
                   <th className="px-4 py-2">PnL ($)</th>
                   <th className="px-4 py-2">PnL (%)</th>
                   <th className="px-4 py-2">Durée (s)</th>
                   <th className="px-4 py-2">Mode</th>
                 </tr>
               </thead>
               <tbody>
                 {trades.map((t, i) => (
                   <tr key={i} className="border-b border-gray-800 hover:bg-gray-800/20">
                     <td className="px-4 py-2 text-xs text-gray-500">{t.trade_id}</td>
                     <td className="px-4 py-2 font-bold">{t.symbol?.name || t.symbol}</td>
                     <td className={`px-4 py-2 font-bold ${t.side === 'LONG' ? 'text-green-400' : 'text-red-400'}`}>{t.side}</td>
                     <td className="px-4 py-2">{Number(t.entry_price).toFixed(5)}</td>
                     <td className="px-4 py-2">{Number(t.exit_price).toFixed(5)}</td>
                     <td className="px-4 py-2">{t.volume}</td>
                     <td className={`px-4 py-2 font-bold ${t.realized_pnl_amount >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                       ${Number(t.realized_pnl_amount).toFixed(2)}
                     </td>
                     <td className={`px-4 py-2 ${t.realized_pnl_percent >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                       {Number(t.realized_pnl_percent).toFixed(2)}%
                     </td>
                     <td className="px-4 py-2">{Number(t.duration_seconds).toFixed(0)}</td>
                     <td className="px-4 py-2 text-xs">{t.mode}</td>
                   </tr>
                 ))}
                 {trades.length === 0 && (
                   <tr>
                     <td colSpan={10} className="px-4 py-8 text-center text-gray-500">
                       Aucun historique disponible.
                     </td>
                   </tr>
                 )}
               </tbody>
             </table>
           </div>
        </div>
      )}
      
      {activeTab === 'data' && <ValidationTab />}
      {activeTab === 'risk' && <CapitalTab />}
      {activeTab === 'council' && <CouncilTab />}
      {activeTab === 'knowledge' && <KnowledgeTab />}

    </div>
  )
}

export default App
