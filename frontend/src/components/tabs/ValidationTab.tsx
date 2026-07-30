
import { useQuery } from '@tanstack/react-query';
import { ShieldCheck, ShieldAlert, Activity, RefreshCw } from 'lucide-react';

interface ValidationMetric {
  name: string;
  status: string;
  value: string;
}

interface ValidationReport {
  verdict: string;
  metrics: ValidationMetric[];
}

export function ValidationTab() {
  const { data, isLoading, error, refetch, isFetching } = useQuery<ValidationReport>({
    queryKey: ['validation'],
    queryFn: async () => {
      const res = await fetch('http://127.0.0.1:8000/api/validation/report');
      if (!res.ok) throw new Error('Failed to fetch validation report');
      return res.json();
    },
    refetchInterval: 15000,
  });

  if (isLoading) {
    return <div className="p-4 text-slate-400">Loading validation data...</div>;
  }

  if (error) {
    return <div className="p-4 text-red-400">Error loading validation report.</div>;
  }

  const report = data || { verdict: 'UNKNOWN', metrics: [] };
  const isGo = report.verdict === 'GO';

  return (
    <div className="space-y-6">
      {/* HEADER: Verdict Banner */}
      <div className={`p-6 rounded-xl border flex items-center justify-between transition-colors ${
        isGo 
          ? 'bg-emerald-900/20 border-emerald-500/30 text-emerald-400' 
          : 'bg-red-900/20 border-red-500/30 text-red-400'
      }`}>
        <div className="flex items-center space-x-4">
          {isGo ? <ShieldCheck size={32} /> : <ShieldAlert size={32} />}
          <div>
            <h2 className="text-2xl font-bold">
              VERDICT: {report.verdict}
            </h2>
            {!isGo && (
              <p className="text-sm mt-1 text-red-300/80">
                Le capital réel reste bloqué tant que ce verdict n'est pas GO.
              </p>
            )}
          </div>
        </div>
        <button 
          onClick={() => refetch()}
          disabled={isFetching}
          className="p-2 rounded hover:bg-white/5 transition-colors disabled:opacity-50"
          title="Rafraîchir"
        >
          <RefreshCw size={20} className={isFetching ? "animate-spin" : ""} />
        </button>
      </div>

      {/* METRICS LIST */}
      <div className="bg-slate-800/50 rounded-xl border border-slate-700/50 p-6">
        <div className="flex items-center space-x-2 mb-4 text-slate-300">
          <Activity size={18} />
          <h3 className="font-semibold text-lg">Critères de Validation</h3>
        </div>
        
        {report.metrics.length === 0 ? (
          <div className="text-slate-500 italic py-4">Aucune métrique disponible ou fichier introuvable.</div>
        ) : (
          <div className="space-y-3">
            {report.metrics.map((metric, i) => (
              <div key={i} className="flex items-center justify-between bg-slate-900/50 p-3 rounded border border-slate-700/30">
                <span className="text-slate-300 font-medium">{metric.name}</span>
                <div className="flex items-center space-x-3">
                  {metric.value && <span className="text-slate-400 text-sm">{metric.value}</span>}
                  <span className={`px-2 py-1 text-xs font-bold rounded ${
                    metric.status === 'PASSED' ? 'bg-emerald-500/20 text-emerald-400' :
                    metric.status === 'FAILED' ? 'bg-red-500/20 text-red-400' :
                    'bg-amber-500/20 text-amber-400'
                  }`}>
                    {metric.status}
                  </span>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
