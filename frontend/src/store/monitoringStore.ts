import { create } from 'zustand';

interface PortfolioSnapshot {
  equity: number;
  cash: number;
  total_unrealized_pnl: number;
  open_positions_count: number;
}

interface RiskSnapshot {
  global_exposure: number;
  distance_to_max_drawdown: number;
  risk_status: string;
}

interface BrokerSnapshot {
  connected: boolean;
  latency_ms: number;
  gateway: string;
  last_heartbeat: string;
}

interface StrategySnapshot {
  id: string;
  status: string;
  running_time: string;
}

interface SystemSnapshot {
  cpu_usage: number;
  memory_usage: number;
  active_services: string[];
  broker_status?: BrokerSnapshot;
  strategy_status?: StrategySnapshot;
}

interface PositionSnapshot {
  symbol: string;
  side: string;
  quantity: number;
  unrealized_pnl: number;
}

interface MonitoringState {
  portfolio: PortfolioSnapshot | null;
  risk: RiskSnapshot | null;
  system: SystemSnapshot | null;
  positions: PositionSnapshot[];
  updateSnapshot: (topic: string, data: any) => void;
}

export const useMonitoringStore = create<MonitoringState>((set) => ({
  portfolio: null,
  risk: null,
  system: null,
  positions: [],
  updateSnapshot: (topic, data) => set((state) => {
    switch (topic) {
      case 'portfolio':
        return { portfolio: data };
      case 'risk':
        return { risk: data };
      case 'system':
        return { system: data };
      case 'positions':
        return { positions: data }; // Assuming data is an array of positions
      default:
        return state;
    }
  }),
}));
