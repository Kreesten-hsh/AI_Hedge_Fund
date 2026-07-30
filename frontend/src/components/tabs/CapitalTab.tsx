
import { useQuery } from '@tanstack/react-query';
import { Wallet, AlertTriangle, CheckCircle2, XCircle } from 'lucide-react';

interface CapitalTier {
  name: string;
  max_drawdown_limit: number;
  current_drawdown: number;
  equity_allocated: number;
  is_active: boolean;
}

export function CapitalTab() {
  const { data: tiers, isLoading, error } = useQuery<CapitalTier[]>({
    queryKey: ['capital'],
    queryFn: async () => {
      const res = await fetch('http://127.0.0.1:8000/api/capital/tiers');
      if (!res.ok) throw new Error('Failed to fetch capital tiers');
      return res.json();
    },
    refetchInterval: 5000,
  });

  if (isLoading) {
    return <div className="p-4 text-slate-400">Loading capital data...</div>;
  }

  if (error) {
    return <div className="p-4 text-red-400">Error loading capital data.</div>;
  }

  if (!tiers || tiers.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-slate-500 border border-slate-800 border-dashed rounded-xl">
        <Wallet size={48} className="mb-4 opacity-50" />
        <p className="text-lg">Aucune segmentation de capital configurée.</p>
        <p className="text-sm">Le système utilise le mode Paper Trading standard sans Global Risk Manager limitant le drawdown par tier.</p>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center space-x-2 text-slate-300">
        <Wallet size={20} />
        <h2 className="text-xl font-semibold">Tiers de Capital (Ségrégation des Risques)</h2>
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {tiers.map((tier, idx) => {
          // current_drawdown is absolute amount, max_drawdown_limit is absolute amount
          const progressPercent = tier.max_drawdown_limit > 0 
            ? Math.max(0, Math.min(100, (tier.current_drawdown / tier.max_drawdown_limit) * 100))
            : 0;
            
          let progressColor = "bg-emerald-500";
          if (progressPercent >= 80) progressColor = "bg-red-500";
          else if (progressPercent >= 50) progressColor = "bg-amber-500";

          return (
            <div key={idx} className={`rounded-xl border p-5 ${tier.is_active ? 'bg-slate-800/80 border-slate-700' : 'bg-red-950/20 border-red-900/50'}`}>
              <div className="flex justify-between items-start mb-4">
                <h3 className="font-bold text-lg text-slate-200">{tier.name}</h3>
                {tier.is_active ? (
                  <span className="flex items-center space-x-1 px-2 py-1 bg-emerald-500/20 text-emerald-400 text-xs font-bold rounded">
                    <CheckCircle2 size={14} /> <span>ACTIF</span>
                  </span>
                ) : (
                  <span className="flex items-center space-x-1 px-2 py-1 bg-red-500/20 text-red-400 text-xs font-bold rounded">
                    <XCircle size={14} /> <span>COUPÉ</span>
                  </span>
                )}
              </div>

              <div className="mb-6">
                <p className="text-sm text-slate-400 mb-1">Équité Actuelle</p>
                <p className="text-2xl font-mono text-slate-100">${tier.equity_allocated.toLocaleString(undefined, {minimumFractionDigits: 2, maximumFractionDigits: 2})}</p>
              </div>

              <div>
                <div className="flex justify-between text-sm mb-2">
                  <span className="text-slate-400">Drawdown</span>
                  <span className="font-mono text-slate-300">
                    ${tier.current_drawdown.toLocaleString(undefined, {maximumFractionDigits: 0})} / ${tier.max_drawdown_limit.toLocaleString(undefined, {maximumFractionDigits: 0})}
                  </span>
                </div>
                <div className="w-full bg-slate-900 rounded-full h-2.5 mb-1 overflow-hidden">
                  <div 
                    className={`h-2.5 rounded-full ${progressColor} transition-all duration-500`}
                    style={{ width: `${progressPercent}%` }}
                  ></div>
                </div>
                {progressPercent >= 80 && tier.is_active && (
                  <p className="text-xs text-red-400 flex items-center mt-2">
                    <AlertTriangle size={12} className="mr-1" /> Proche du plafond
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
