# Protocol: Live Trading Safety (Micro Capital)

This document formalizes the rigorous procedure for transitioning Aegis Quant OS from Demo to Real Trading mode, minimizing financial risk.

## 1. Prerequisites (NO-GO without passing)
- A successful continuous Demo Paper Trading cycle must be completed.
- Conditions for cycle completion: **Minimum 200 trades AND 2 weeks duration (both must be met)**.
- Re-run all validators (`BenchmarkGate`, `TickReplayEngine`, `ShadowTradingEngine`) against the real generated data.
- Ensure the `VALIDATION_PIPELINE_REPORT.md` is populated with REAL metrics, no "(Simulated)" tags, and the `BenchmarkGate` officially issues a GO.

## 2. Transition Procedure (Demo -> Live)
1. **Approval**: Confirm the `VALIDATION_PIPELINE_REPORT.md` states GO.
2. **Environment Variable Setup**: 
   - `export AEGIS_ENV=LIVE`
   - `export DERIV_LIVE_TOKEN=your_real_token`
3. **Gateway Configuration**: 
   - Ensure the orchestrator is configured to instantiate `LiveDerivGateway`.
   - Pass the mandatory flag: `i_understand_this_is_real_money=True` in code.
4. **Capital Allocation Setup**:
   - For Phase 2, initial capital is strictly $50.00.
   - Configure a single `CapitalTier` of $50 with a strict absolute drawdown ceiling (e.g., $10 max loss).
5. **Risk Configuration**:
   - `GlobalRiskManager` must be instantiated with a stricter config than demo (e.g., `max_drawdown=0.02`).

## 3. During Live Trading
- **Spread Cost Monitoring**: Cumulative spread must be tracked daily to ensure HFT/Scalping profitability isn't eroded by transaction costs.
- **Goal**: Maintain 100-200 trades per day, leveraging small continuous opportunities.

## 4. Emergency Stop (Kill Switch)
- **Automatic**: If a tier's absolute drawdown limit is hit, `CapitalTier` deactivates. `GlobalRiskManager` instantly blocks all future opening trades for that tier.
- **Manual**: To hard-stop the system, kill the orchestrator process and/or change `AEGIS_ENV` to anything other than `LIVE`. This will immediately trigger a `SecurityError` upon the next order submission attempt.
