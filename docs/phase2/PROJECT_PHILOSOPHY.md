# Philosophie du Projet : Aegis Quant OS

> **Document annoté le 2026-07-31** sur la base de `docs/refont/AUDIT_COMPLET_2026-07-31.md` (verdict **NO-GO**).
>
> **Les principes de ce document ne sont pas modifiés : ils sont la raison d'être du projet.** Ce qui est
> corrigé, c'est la liste de l'écosystème, qui présentait dix composants comme des **organes en place**
> (« le système nerveux », « les sens », « la mémoire »). Mesure par grep : la plupart n'ont aucun site
> d'appel en production. Une métaphore anatomique appliquée à du code non câblé fait croire que le corps
> est vivant.

## Règle Absolue

**Aegis n'est PAS un robot de trading.**
Aegis ne doit pas être conçu comme une boîte noire ou un SaaS B2C, mais comme le propre hedge fund
personnel de son créateur.

Aegis est un **Système d'Exploitation Quantitatif (Quantitative Operating System)** : un environnement de
recherche, d'entraînement, de décision et d'exécution, capable d'apprendre de son historique.

Ce principe reste intact. Il est même la raison pour laquelle la falsification documentaire est grave :
un hedge fund personnel n'a aucun investisseur à rassurer, donc aucune raison de se mentir à lui-même.

## Objectif rappelé

L'objectif n'a pas changé : **démo réelle sur Deriv pour entraîner le système, puis capital réel.**

C'est précisément cet objectif qui interdit de laisser la liste ci-dessous en l'état. Un composant
décrit comme « le système nerveux » et qui, mesuré, renvoie `return "mock_id"` n'est pas un organe
faible : c'est une absence d'organe, présentée comme une présence.

## Vocabulaire de statut (identique aux autres documents Phase 2)

| Marqueur | Signification mesurable |
| --- | --- |
| `[ ]` | Rien n'existe dans le dépôt. |
| `[ÉCRIT-NON-CÂBLÉ]` | Code présent, **zéro site d'appel en production**. |
| `[CÂBLÉ-NON-VALIDÉ]` | Appelé en production, aucune validation franchie. |
| `[FAÇADE]` | Retourne une constante, un mock ou une donnée aléatoire au lieu de calculer. |
| `[VENDORÉ]` | Code amont copié dans le dépôt (question de licence, pas d'intégration). |
| `[INSPIRATION]` | Décision explicite : jamais intégré, sert de référence de conception. |
| `[ABANDONNÉ]` | Évalué puis écarté, rien dans le dépôt sur le chemin de production. |
| `[VALIDÉ]` | Cycle réel, données réelles, `git_version` + `data_hash` traçables. |

## L'écosystème visé — et son état mesuré

La colonne « Rôle visé » est la formulation d'origine : elle décrit l'intention, elle reste juste.
La colonne « Statut mesuré » dit ce que le dépôt fait aujourd'hui. Détail complet dans
`DEPENDENCY_MATRIX.md`, qui fait foi pour les dépendances.

| Composant | Rôle visé | Statut mesuré | Preuve |
| --- | --- | --- | --- |
| **vn.py** | Le système nerveux (Exécution) | `[CÂBLÉ-NON-VALIDÉ]` | Route réellement des ordres, mais `on_trade` a pour corps `pass` (`infrastructure/live/vnpy/execution.py:69`) et `return "mock_id"` (`:46`). Aucun retour d'exécution ne remonte au portefeuille. Contourne le `RiskEngine` sur 3 chemins. |
| **OpenBB** | La source de données (Sens) | `[ÉCRIT-NON-CÂBLÉ]` | `infrastructure/data/providers/openbb_provider.py` existe, zéro site d'appel en production. |
| **Qlib** | Le laboratoire quantitatif | `[ÉCRIT-NON-CÂBLÉ]` | Aucun cycle de production n'appelle `QlibPredictor`. Deux `DatasetBuilder` divergents. |
| **Kronos** | Le moteur de prévision temporelle | `[FAÇADE]` + `[VENDORÉ]` | `providers/kronos_adapter.py:40-41,63-71` prédit sur `np.random.randn` — le modèle infère sur du bruit. 1 532 lignes amont vendorées **sans LICENSE**. |
| **FinRL** | Le moteur d'apprentissage (RL) | `[ÉCRIT-NON-CÂBLÉ]` | `PolicyTrainer(`, `PolicyEvaluator(` : 0 site d'appel. L'observation passée en production est `np.zeros(30)` (`application/council/orchestrator.py:97`). |
| **FinGPT** | L'analyste macro-économique | `[ABANDONNÉ]` | Remplacé par Ollama selon `ADR-002`. Mais la production injecte `MockReasoner()` (`api/deps.py:53`) : **aucun analyste macro n'existe**, ni FinGPT ni Ollama. |
| **FAISS/ChromaDB** | La mémoire des expériences | `[ÉCRIT-NON-CÂBLÉ]` | `FaissVectorStore` présent, index jamais alimenté : `MemoryManager(` compte 0 occurrence hors définition. Une mémoire jamais écrite ne se souvient de rien. |
| **TradingAgents** | L'orchestration du conseil | `[INSPIRATION]` | **Décision d'architecture explicite, pas une lacune.** Le comité est écrit maison (`IVotingAgent`, `MultiAgentCouncil`, `VoteAggregator`, `ConflictResolver`) en s'inspirant de ce dépôt. Rien à intégrer, rien à rattraper. |
| **Risk Manager** | L'autorité déterministe finale (Veto) | `[CÂBLÉ-NON-VALIDÉ]` | Le `RiskEngine` existe et est appelé, mais **4 chemins d'ordre le contournent** (`api/routers/positions.py:43`, `providers/vnpy_adapter.py:52,57,79`, `infrastructure/live/vnpy/execution.py:14,47`). Une autorité contournable n'est pas finale. Lot 1. |
| **Trading Control Center** | Centre d'opérations et de supervision | `[FAÇADE]` | Le dashboard affiche `cpu_usage=0.0`, `BrokerSnapshot(connected=True, latency_ms=12.5, gateway="BINANCE")` — alors que le broker du projet est Deriv — et `StrategySnapshot(status="Live", running_time="14h 22m")` en dur (`application/monitoring/engine.py:60-78`). Supervision d'un état inventé. |

**Aucun composant `[VALIDÉ]` au 2026-07-31.**

## La Priorité : La Survie

La priorité n'est **PAS** de gagner beaucoup.
La priorité est de **survivre**.

Ce principe est aujourd'hui **contredit par le code, pas par le texte**. Survivre suppose un veto
inviolable ; quatre chemins d'ordre contournent le `RiskEngine`. Survivre suppose de connaître son
drawdown ; `orchestrator.py:169-184` le calcule sur des valeurs constantes. Le Lot 1 et le Lot 2 du
plan de correction ne sont pas des améliorations techniques : ce sont les conditions pour que cette
section cesse d'être un vœu.

## Métrique de Succès

Une journée à **+0,4 %** est meilleure qu'une journée à **+5 %** suivie d'un drawdown de **-12 %**.

Cette métrique reste la bonne. Elle n'est simplement mesurable sur rien aujourd'hui : aucun cycle réel
n'a jamais tourné (`VALIDATION_PIPELINE_REPORT.md`), et le P&L est calculé par trois implémentations
divergentes (`engine/portfolio.py:92-93`, `engine/backtester.py:180-188`,
`application/monitoring/engine.py:126-129`) — Lot 3.

## Ce que ce document ne promet pas

- **Pas un inventaire de composants opérationnels.** Le tableau ci-dessus est un état mesuré à une date,
  pas une architecture livrée.
- **Pas de dette rattrapable en marge.** Trois composants sur dix sont des façades : ils produisent une
  sortie plausible à partir de rien. C'est plus grave qu'un composant absent, parce que ça passe les
  yeux d'un relecteur.
- **Pas de lacune sur TradingAgents ni AutoHedge.** Ce sont des références de conception assumées.
  Quiconque les lit comme des intégrations manquantes se trompe de lecture.

---

*Cette philosophie guide l'ensemble du développement, l'architecture du code, la gestion des risques et
la conception de la fonction de récompense de l'IA. Elle n'a jamais été le problème — l'écart entre elle
et le code l'était.*
