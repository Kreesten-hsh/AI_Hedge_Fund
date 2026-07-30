
import { useQuery } from '@tanstack/react-query';
import { Users, Gavel, AlertOctagon, TrendingUp, TrendingDown, Minus } from 'lucide-react';

interface AgentVote {
  agent_name: string;
  direction: string;
  confidence: number;
}

interface CouncilVerdict {
  final_vote: string;
  aggregated_confidence: number;
  position_size_multiplier: number;
  votes: AgentVote[];
  veto_reason: string | null;
  disagreement_level: number;
}

interface RLPolicy {
  risk_multiplier: number;
  confidence_threshold_adjustment: number;
  agent_weights: Record<string, number>;
}

interface CouncilStatus {
  verdict: CouncilVerdict | null;
  policy: RLPolicy | null;
}

export function CouncilTab() {
  const { data, isLoading, error } = useQuery<CouncilStatus>({
    queryKey: ['council'],
    queryFn: async () => {
      const res = await fetch('http://127.0.0.1:8000/api/council/latest');
      if (!res.ok) throw new Error('Failed to fetch council status');
      return res.json();
    },
    refetchInterval: 2000,
  });

  if (isLoading) {
    return <div className="p-4 text-slate-400">Loading council data...</div>;
  }

  if (error) {
    return <div className="p-4 text-red-400">Error loading council data.</div>;
  }

  if (!data?.verdict) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-slate-500 border border-slate-800 border-dashed rounded-xl">
        <Users size={48} className="mb-4 opacity-50" />
        <p className="text-lg">Aucune décision du conseil disponible.</p>
        <p className="text-sm">En attente du prochain événement de marché pour déclencher le vote des agents...</p>
      </div>
    );
  }

  const { verdict, policy } = data;
  const sortedVotes = [...verdict.votes].sort((a, b) => b.confidence - a.confidence);

  // Helper for direction colors
  const getDirColor = (dir: string) => {
    if (dir === 'LONG') return 'text-emerald-400 bg-emerald-500/10 border-emerald-500/20';
    if (dir === 'SHORT') return 'text-red-400 bg-red-500/10 border-red-500/20';
    return 'text-slate-400 bg-slate-500/10 border-slate-500/20';
  };

  const getDirIcon = (dir: string) => {
    if (dir === 'LONG') return <TrendingUp size={16} className="mr-2" />;
    if (dir === 'SHORT') return <TrendingDown size={16} className="mr-2" />;
    return <Minus size={16} className="mr-2" />;
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center space-x-2 text-slate-300">
        <Users size={20} />
        <h2 className="text-xl font-semibold">Council & RL Policy</h2>
      </div>

      {/* FINAL VERDICT BANNER */}
      <div className={`p-6 rounded-xl border flex flex-col md:flex-row md:items-center justify-between ${getDirColor(verdict.final_vote)}`}>
        <div className="flex items-center space-x-4 mb-4 md:mb-0">
          <Gavel size={32} />
          <div>
            <p className="text-sm opacity-80 font-medium">Verdict Final</p>
            <h3 className="text-3xl font-bold flex items-center">
              {getDirIcon(verdict.final_vote)}
              {verdict.final_vote}
            </h3>
          </div>
        </div>
        <div className="flex space-x-6 text-sm">
          <div>
            <p className="opacity-70">Confiance</p>
            <p className="font-mono text-lg font-semibold">{(verdict.aggregated_confidence * 100).toFixed(1)}%</p>
          </div>
          <div>
            <p className="opacity-70">Taille de Position</p>
            <p className="font-mono text-lg font-semibold">{verdict.position_size_multiplier.toFixed(2)}x</p>
          </div>
        </div>
      </div>

      {/* VETO ALERT */}
      {verdict.veto_reason && (
        <div className="p-4 bg-red-950/40 border border-red-900/60 rounded-lg flex items-start space-x-3 text-red-400">
          <AlertOctagon size={20} className="shrink-0 mt-0.5" />
          <div>
            <h4 className="font-bold">Veto Actif</h4>
            <p className="text-sm text-red-300/80">{verdict.veto_reason}</p>
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* AGENTS VOTES */}
        <div className="bg-slate-800/40 rounded-xl border border-slate-700/50 p-5">
          <div className="flex justify-between items-end mb-4">
            <h3 className="font-semibold text-slate-200">Votes des Agents</h3>
            <div className="text-right">
              <p className="text-xs text-slate-400 mb-1">Désaccord Global</p>
              <div className="w-24 bg-slate-900 rounded-full h-1.5 overflow-hidden flex">
                <div 
                  className={`h-full ${verdict.disagreement_level > 0.6 ? 'bg-red-500' : verdict.disagreement_level > 0.3 ? 'bg-amber-500' : 'bg-emerald-500'}`} 
                  style={{ width: `${verdict.disagreement_level * 100}%` }}
                ></div>
              </div>
            </div>
          </div>
          
          <div className="space-y-2">
            {sortedVotes.map((vote, idx) => (
              <div key={idx} className="flex items-center justify-between p-2.5 rounded bg-slate-900/50 border border-slate-800">
                <span className="font-medium text-slate-300 text-sm">{vote.agent_name}</span>
                <div className="flex items-center space-x-3">
                  <span className={`flex items-center px-2 py-1 rounded border text-xs font-bold ${getDirColor(vote.direction)}`}>
                    {getDirIcon(vote.direction)}
                    {vote.direction}
                  </span>
                  <span className="font-mono text-xs text-slate-400 w-12 text-right">
                    {(vote.confidence * 100).toFixed(0)}%
                  </span>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* RL POLICY WEIGHTS */}
        <div className="bg-slate-800/40 rounded-xl border border-slate-700/50 p-5">
          <h3 className="font-semibold text-slate-200 mb-4">Politique RL Actuelle</h3>
          {!policy ? (
            <div className="text-slate-500 text-sm italic py-4">Poids égaux (Politique non définie)</div>
          ) : (
            <div className="space-y-4">
              <div className="grid grid-cols-2 gap-4 mb-6">
                <div className="bg-slate-900/50 p-3 rounded border border-slate-800">
                  <p className="text-xs text-slate-400 mb-1">Multiplicateur de Risque</p>
                  <p className="font-mono font-medium text-slate-200">{policy.risk_multiplier.toFixed(2)}x</p>
                </div>
                <div className="bg-slate-900/50 p-3 rounded border border-slate-800">
                  <p className="text-xs text-slate-400 mb-1">Ajustement Seuil Confiance</p>
                  <p className="font-mono font-medium text-slate-200">{policy.confidence_threshold_adjustment > 0 ? '+' : ''}{policy.confidence_threshold_adjustment.toFixed(2)}</p>
                </div>
              </div>
              
              <div>
                <h4 className="text-sm font-medium text-slate-300 mb-3">Poids des Agents</h4>
                <div className="space-y-3">
                  {Object.entries(policy.agent_weights)
                    .sort(([, a], [, b]) => b - a)
                    .map(([agent, weight]) => (
                    <div key={agent}>
                      <div className="flex justify-between text-xs mb-1">
                        <span className="text-slate-400">{agent}</span>
                        <span className="font-mono text-slate-300">{(weight * 100).toFixed(1)}%</span>
                      </div>
                      <div className="w-full bg-slate-900 rounded-full h-1.5 overflow-hidden">
                        <div 
                          className="bg-indigo-500 h-full rounded-full" 
                          style={{ width: `${Math.max(2, weight * 100)}%` }}
                        ></div>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
