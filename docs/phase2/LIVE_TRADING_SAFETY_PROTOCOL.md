# Protocol: Live Trading Safety (Micro Capital)

> # ⛔ AVERTISSEMENT — NE PAS EXÉCUTER CETTE PROCÉDURE (2026-07-31)
>
> **Ce protocole est exécutable tel quel, et chacun de ses mécanismes de sécurité est mesuré comme
> non fonctionnel.** Suivre les étapes 1 à 5 aujourd'hui reviendrait à engager du capital réel derrière
> un système qui se croit surveillé et ne l'est pas.
>
> Faits mesurés (audit `docs/refont/AUDIT_COMPLET_2026-07-31.md`, verdict **NO-GO**) :
>
> 1. **Le kill switch ne peut pas se déclencher.** `CapitalTier` se désactive sur seuil de drawdown, mais
>    le drawdown n'est jamais mis à jour : `on_trade` a pour corps `pass`
>    (`infrastructure/live/vnpy/execution.py:69`), donc **aucun retour d'exécution ne remonte au
>    portefeuille**, et le drawdown est de surcroît une constante (`orchestrator.py:169-184`). Un plafond
>    de perte qu'aucune mesure n'alimente n'est pas un plafond.
> 2. **Le `RiskEngine` est contournable sur 4 chemins** (dont `providers/vnpy_adapter.py:52,57,79`). Le
>    CLAUDE.md pose son autorité comme absolue ; le code ne la tient pas.
> 3. **Le « GO » du `BenchmarkGate` n'a pas de valeur.** Des validateurs retournent `passed=True` écrit en
>    dur. L'étape 1 exige un GO que le code délivre inconditionnellement.
> 4. **Le prérequis « 200 trades » est inatteignable.** Le comité produit
>    `VERDICT: WAIT | mult=0.0 | conf=0.0` à chaque cycle : zéro trade ouvert, zéro trade consigné.
> 5. **Aucun flux de prix temps réel n'existe.** Aucune souscription WebSocket dans le dépôt. Le système
>    ne voit pas le marché sur lequel on lui demanderait de risquer de l'argent.
> 6. **`send_order` renvoie `return "mock_id"`** (`infrastructure/live/vnpy/execution.py:46`).
>
> **Condition de levée :** Lots 0 à 4 exécutés et vérifiés, puis un cycle démo réel complet. Aucune
> exception, y compris pour un capital de 50 $ — le montant limite la perte, il ne valide rien.
>
> Le texte du protocole est conservé intégralement ci-dessous : sa procédure est bonne, c'est le socle
> technique qui manque.

This document formalizes the rigorous procedure for transitioning Aegis Quant OS from Demo to Real Trading mode, minimizing financial risk.

## Objectif rappelé

**Démo réelle sur Deriv pour entraîner le système, puis capital réel.** Ce document est le passage entre
les deux. C'est le seul fichier du dépôt dont une erreur coûte de l'argent directement, et non du temps.


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

   > **Note de sécurité (2026-07-31) :** un token Deriv réel ne doit jamais être écrit dans un fichier
   > suivi par git, ni dans un historique shell persistant. L'audit a relevé le sujet des credentials
   > commités : à traiter avant toute manipulation de token réel (Lot 0).

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

> **Correctif de statut (2026-07-31) :** aucun des deux points n'est instrumenté. Aucun cumul de spread
> n'existe dans le dépôt, et aucun compteur de fréquence d'exécution non plus (`BENCHMARKS.md`, §2). La
> cible « 100-200 trades/jour » est à comparer aux **0 trades** actuellement produits par cycle
> (`VERDICT: WAIT | mult=0.0 | conf=0.0`). Ce n'est pas un écart de réglage, c'est un écart de nature.

## 4. Emergency Stop (Kill Switch)
- **Automatic**: If a tier's absolute drawdown limit is hit, `CapitalTier` deactivates. `GlobalRiskManager` instantly blocks all future opening trades for that tier.
- **Manual**: To hard-stop the system, kill the orchestrator process and/or change `AEGIS_ENV` to anything other than `LIVE`. This will immediately trigger a `SecurityError` upon the next order submission attempt.

> **Correctif de statut (2026-07-31) — le plus grave du document.**
>
> **L'arrêt automatique est inopérant.** Il dépend du drawdown d'un `CapitalTier` ; ce drawdown n'est
> jamais alimenté par les exécutions (`on_trade` corps `pass`, `infrastructure/live/vnpy/execution.py:69`)
> et il est calculé sur constantes (`orchestrator.py:169-184`). Le seuil ne sera donc jamais franchi,
> quelle que soit la perte réelle. Un kill switch qui ne mesure rien ne coupe rien.
>
> **L'arrêt manuel n'est fiable que sur sa première moitié.** Tuer le processus fonctionne — c'est
> aujourd'hui le seul mécanisme d'arrêt réellement effectif. Le basculement d'`AEGIS_ENV`, lui, ne
> protège que le chemin de soumission qui vérifie cette variable ; les **4 chemins qui contournent le
> `RiskEngine`** ne la consultent pas.
>
> **Conséquence opérationnelle, à retenir telle quelle :** en cas d'incident sur capital réel, la seule
> action fiable est de **tuer le processus de l'orchestrateur**. Ne pas compter sur le seuil de
> drawdown, ni sur `AEGIS_ENV`. Rétablir un veto réellement inviolable est l'objet du Lot 1.

## Ce que ce document ne promet pas

- **Pas de sécurité.** La procédure est correcte ; les mécanismes qu'elle invoque ne fonctionnent pas.
  Le suivre à la lettre aujourd'hui ne protège pas le capital.
- **Pas de plafond de perte.** Le « ceiling » de 10 $ sur un tier de 50 $ suppose une mesure de perte qui
  n'existe pas. La perte réelle n'est pas bornée par le code, seulement par le solde du compte.
- **Pas de franchissement possible du prérequis.** « 200 trades sur 2 semaines » ne peut pas être atteint
  tant que le comité vote `WAIT` à l'unanimité. Ce prérequis n'est pas en attente : il est bloqué en amont.

