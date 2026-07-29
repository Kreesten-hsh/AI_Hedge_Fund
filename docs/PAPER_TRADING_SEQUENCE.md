# Séquences du Paper Trading (PT-01)

## Cycle de vie complet d'un Ordre

Ce diagramme illustre comment un Signal émis par une stratégie traverse le Risk Manager, est converti en Ordre de Paper Trading, simulé via les moteurs physiques, et met à jour le Portefeuille.

```mermaid
sequenceDiagram
    participant Strategy
    participant Orchestrator
    participant RiskManager
    participant PaperBroker
    participant PhysicsEngines as Slippage/Latency/Commission
    participant EventBus
    
    Strategy->>Orchestrator: SignalEvent(BUY, AAPL)
    Orchestrator->>RiskManager: evaluate_order(OrderEvent)
    
    alt Risk Rejected
        RiskManager-->>Orchestrator: False (Max Drawdown reached)
        Orchestrator--xOrchestrator: Order dropped
    else Risk Approved
        RiskManager-->>Orchestrator: True
        
        Orchestrator->>PaperBroker: submit_order(PaperOrder)
        PaperBroker->>EventBus: OrderLifecycleEvent(SUBMITTED)
        
        PaperBroker->>PaperBroker: Validate Margin / Portfolio
        alt Insufficient Margin
            PaperBroker->>EventBus: OrderLifecycleEvent(REJECTED)
            PaperBroker-->>Orchestrator: PaperExecutionReport(Rejected)
        else Margin Valid
            PaperBroker->>EventBus: OrderLifecycleEvent(ACCEPTED)
            
            PaperBroker->>PhysicsEngines: simulate_latency()
            PhysicsEngines-->>PaperBroker: latency (ms)
            
            PaperBroker->>PhysicsEngines: calculate_slippage()
            PhysicsEngines-->>PaperBroker: slippage
            
            PaperBroker->>PhysicsEngines: calculate_commission()
            PhysicsEngines-->>PaperBroker: commission
            
            PaperBroker->>PaperBroker: Apply Fill & Update Balances/Positions
            PaperBroker->>EventBus: OrderLifecycleEvent(FILLED)
            PaperBroker->>EventBus: AccountEvent(balance_updated)
            PaperBroker->>EventBus: PositionEvent(opened)
            
            PaperBroker-->>Orchestrator: PaperExecutionReport(Filled)
        end
    end
```

## Boucle de Monitoring (Snapshots)

```mermaid
sequenceDiagram
    participant Orchestrator
    participant PaperBroker
    participant Dashboard / EventBus
    
    loop Every 5 seconds
        Orchestrator->>PaperBroker: get_account_state()
        PaperBroker-->>Orchestrator: PaperAccount(Balances, Positions)
        Orchestrator->>Orchestrator: Compute PaperPortfolioSnapshot (Equity, Exposure, PnL)
        Orchestrator->>Dashboard / EventBus: Emit Metrics
    end
```
