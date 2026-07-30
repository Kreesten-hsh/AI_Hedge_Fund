import { useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Brain, Filter, Info, ChevronDown, ChevronUp } from 'lucide-react';

interface KnowledgeScore {
  confidence: number;
  support: number;
  frequency: number;
  stability: number;
  recency: number;
}

interface Knowledge {
  id: string;
  type: string;
  description: string;
  features_conditions: Record<string, Record<string, number>>;
  score: KnowledgeScore;
}

export function KnowledgeTab() {
  const [selectedType, setSelectedType] = useState<string>('ALL');
  const [expandedId, setExpandedId] = useState<string | null>(null);

  const { data: rules, isLoading, error } = useQuery<Knowledge[]>({
    queryKey: ['knowledge'],
    queryFn: async () => {
      const res = await fetch('http://127.0.0.1:8000/api/knowledge/rules');
      if (!res.ok) throw new Error('Failed to fetch knowledge rules');
      return res.json();
    },
    refetchInterval: 10000,
  });

  if (isLoading) {
    return <div className="p-4 text-slate-400">Loading knowledge base...</div>;
  }

  if (error) {
    return <div className="p-4 text-red-400">Error loading knowledge base.</div>;
  }

  const safeRules = rules || [];
  const types = ['ALL', ...Array.from(new Set(safeRules.map(r => r.type)))];
  
  const filteredRules = safeRules
    .filter(r => selectedType === 'ALL' || r.type === selectedType)
    .sort((a, b) => b.score.confidence - a.score.confidence);

  return (
    <div className="space-y-6">
      {/* HEADER & DISCLAIMER */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div className="flex items-center space-x-2 text-slate-300">
          <Brain size={20} />
          <h2 className="text-xl font-semibold">Base de Connaissances Active</h2>
        </div>
        
        <div className="bg-amber-900/30 border border-amber-500/50 text-amber-300 text-xs px-3 py-2 rounded flex items-center space-x-2 max-w-md">
          <Info size={16} className="shrink-0" />
          <p>Généré sans résumé LLM (MockReasoner actif) — règles statistiques uniquement.</p>
        </div>
      </div>

      {/* FILTER */}
      <div className="flex items-center space-x-3 text-sm">
        <Filter size={16} className="text-slate-400" />
        <div className="flex flex-wrap gap-2">
          {types.map(t => (
            <button
              key={t}
              onClick={() => setSelectedType(t)}
              className={`px-3 py-1 rounded-full border transition-colors ${
                selectedType === t 
                  ? 'bg-indigo-600 text-white border-indigo-500' 
                  : 'bg-slate-800 text-slate-400 border-slate-700 hover:bg-slate-700 hover:text-slate-300'
              }`}
            >
              {t}
            </button>
          ))}
        </div>
      </div>

      {/* RULES LIST */}
      {filteredRules.length === 0 ? (
        <div className="text-center py-12 text-slate-500 border border-slate-800 border-dashed rounded-xl">
          Aucune règle trouvée.
        </div>
      ) : (
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-4">
          {filteredRules.map(rule => {
            const isExpanded = expandedId === rule.id;
            return (
              <div key={rule.id} className="bg-slate-800/60 border border-slate-700/60 rounded-xl overflow-hidden transition-all">
                <div 
                  className="p-4 cursor-pointer hover:bg-slate-700/30 flex justify-between items-start"
                  onClick={() => setExpandedId(isExpanded ? null : rule.id)}
                >
                  <div className="pr-4">
                    <div className="flex items-center space-x-2 mb-1">
                      <span className="text-xs font-bold px-2 py-0.5 rounded bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">
                        {rule.type}
                      </span>
                      <span className="text-xs text-slate-500 font-mono">{rule.id.substring(0, 8)}...</span>
                    </div>
                    <p className="text-slate-200 text-sm font-medium leading-relaxed">{rule.description}</p>
                  </div>
                  <div className="flex flex-col items-end shrink-0">
                    <span className="text-xs text-slate-400 mb-1">Confiance</span>
                    <span className="text-lg font-mono font-bold text-emerald-400">
                      {(rule.score.confidence * 100).toFixed(1)}%
                    </span>
                    {isExpanded ? <ChevronUp size={16} className="text-slate-500 mt-2" /> : <ChevronDown size={16} className="text-slate-500 mt-2" />}
                  </div>
                </div>

                {isExpanded && (
                  <div className="p-4 bg-slate-900/50 border-t border-slate-700/50">
                    <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 mb-5">
                      <ScoreGauge label="Support" value={rule.score.support} max={100} isInt />
                      <ScoreGauge label="Frequency" value={rule.score.frequency} max={1} />
                      <ScoreGauge label="Stability" value={rule.score.stability} max={1} />
                      <ScoreGauge label="Recency" value={rule.score.recency} max={1} />
                    </div>
                    
                    <div>
                      <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">Conditions Statistiques (Brutes)</h4>
                      <div className="bg-black/40 rounded p-3 overflow-x-auto border border-slate-800">
                        <pre className="text-xs text-slate-300 font-mono">
                          {JSON.stringify(rule.features_conditions, null, 2)}
                        </pre>
                      </div>
                    </div>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

function ScoreGauge({ label, value, max, isInt = false }: { label: string, value: number, max: number, isInt?: boolean }) {
  const percentage = Math.max(0, Math.min(100, (value / max) * 100));
  
  return (
    <div>
      <div className="flex justify-between items-end mb-1">
        <span className="text-xs text-slate-500">{label}</span>
        <span className="text-xs font-mono font-medium text-slate-300">
          {isInt ? value.toString() : value.toFixed(2)}
        </span>
      </div>
      <div className="w-full bg-slate-800 rounded-full h-1.5 overflow-hidden">
        <div 
          className="bg-indigo-400 h-full rounded-full" 
          style={{ width: `${percentage}%` }}
        ></div>
      </div>
    </div>
  );
}
