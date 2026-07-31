# Benchmarks et Objectifs Qualitatifs

> **Document annoté le 2026-07-31** sur la base de `docs/refont/AUDIT_COMPLET_2026-07-31.md` (verdict **NO-GO**).
>
> **Les seuils de ce fichier ne sont pas modifiés : ils sont corrects.** C'est le seul document de
> `docs/phase2/` dont les chiffres correspondent au code. `Win Rate > 85 %` et `Sortino > 2.0` sont exactement
> ce qu'applique `benchmark_gate.py:14-15`. La contradiction relevée à l'audit venait de l'autre côté :
> l'ancienne version de `VALIDATION_PIPELINE_REPORT.md:16` annonçait `0.55` et `1.2`. Ce fichier fait foi ;
> l'arbitrage reste à consigner dans un ADR (Lot 5).
>
> Ce qui est ajouté ici est une colonne manquante : **est-ce que quelque chose, dans le dépôt, sait mesurer
> cette métrique aujourd'hui ?** Un objectif sans instrument de mesure n'est pas un critère de déploiement,
> c'est une intention.

## Objectif rappelé

Ces seuils sont la porte entre la **démo réelle** et le **capital réel**. Une métrique déclarée mais non
instrumentée laisse cette porte ouverte sans surveillance. C'est la raison d'être de la colonne « Mesurable
aujourd'hui ».

Chaque nouvelle itération de l'IA (ou chaque nouveau modèle) **doit** battre la version précédente sur ces
critères pour être déployée en production. Cette règle reste en vigueur — elle n'a simplement jamais été
appliquée, faute de mesure réelle.

## 1. Métriques de performance et de risque

| Métrique | Objectif | Mesurable aujourd'hui | Preuve |
|---|---|---|---|
| Sharpe Ratio | > 1.5 | **Non fiable** | Deux annualisations divergentes (`engine/portfolio.py:227` vs `engine/performance.py:70,74`). Deux chiffres possibles pour la même série (Lot 3). |
| Sortino Ratio | > 2.0 | **Non fiable** | Même divergence d'annualisation. Seuil conforme à `benchmark_gate.py:15`. |
| Win Rate | > 85 % (micro-scalping) | **Non** | Le PnL a 3 implémentations divergentes (`engine/portfolio.py:92-93`, `engine/backtester.py:180-188`, `application/monitoring/engine.py:126-129`) et le prix d'exécution est la constante `Decimal("100.0")` (`application/council/orchestrator.py:87`). Seuil conforme à `benchmark_gate.py:14`. |
| Average Win / Average Loss | Stable, même si < 1 | **Non** | Aucun calcul de ce ratio dans le dépôt. Métrique déclarée, jamais implémentée. |
| Max Drawdown | < 5 % | **Non** | Le drawdown en production est constant (`application/council/orchestrator.py:169-184`, points morts `:172,173,184`). Le kill switch adossé à ce seuil ne peut structurellement pas se déclencher. |
| Recovery Factor | < 48 h | **Non** | Aucun calcul dans le dépôt. Dépend d'un drawdown réel, donc bloqué en amont. |

## 2. Métriques opérationnelles et techniques

| Métrique | Objectif | Mesurable aujourd'hui | Preuve |
|---|---|---|---|
| Latency (tick-to-trade) | < 20 ms | **Non** | `latency_ms = 50.0` est une constante (`orchestrator.py:88`), et aucun tick réel n'entre : aucun abonnement WebSocket de prix dans le dépôt. La latence affichée dépasse d'ailleurs le seuil qu'elle prétend surveiller. |
| Trades/day | ~100 à 200 | **Non** | Aucun compteur de fréquence d'exécution dans le dépôt. Métrique déclarée, jamais implémentée. |
| Slippage moyen | < 0.5 pip | **Non** | `ShadowTradingEngine` compare un prix de décision à un prix d'exécution constant. Le slippage obtenu est une fonction d'une constante. |
| Spread cumulé | < gains bruts du jour | **Non** | Aucun cumul de spread dans le dépôt. Métrique déclarée, jamais implémentée. |

## 3. Métriques système (observabilité)

| Métrique | Objectif | Mesurable aujourd'hui | Preuve |
|---|---|---|---|
| CPU Usage | < 60 % | **Non — valeur falsifiée** | `cpu_usage=0.0` en dur (`application/monitoring/engine.py:60-78`). Le même bloc publie `BrokerSnapshot(connected=True, latency_ms=12.5, gateway="BINANCE")` alors que le broker du projet est Deriv, et `StrategySnapshot(status="Live", running_time="14h 22m")`. Le dashboard affiche une santé système inventée (Lot 6). |
| RAM Usage | < 4 GB hors modèles ML isolés | **Partiellement** | Le seul chiffre mesuré du dépôt concerne Kronos : ~917 MB (`RESEARCH_LOGBOOK.md`, entrée de gouvernance « Intégration Kronos (Sprint AI-08) »), ce qui contredit l'empreinte « <300MB » annoncée ailleurs. Aucune surveillance continue. |
| Vector DB Query Time | < 5 ms sur 200 voisins | **Non** | L'index FAISS n'est jamais alimenté : `MemoryManager(` compte 0 occurrence hors définition. Mesurer une recherche sur un index vide n'a pas de sens. |

## Ce que ce document ne promet pas

- **Pas de rentabilité.** Ces seuils filtrent ; ils ne produisent pas de gain.
- **Pas que ces seuils seront atteints.** Ils sont volontairement sévères (`Win Rate > 85 %`). Une fois les
  validateurs réels (Lot 4), il est possible qu'aucune stratégie actuelle ne les franchisse. Conformément à
  `CLAUDE.md`, **un rejet propre et reproductible est un progrès.**
- **Pas de mesure avant les Lots 2 et 3.** 12 des 13 métriques ci-dessus ne sont pas mesurables aujourd'hui.
  Comparer une itération à la précédente est donc impossible en l'état — la règle de non-régression du
  paragraphe d'ouverture n'a jamais pu être appliquée.
