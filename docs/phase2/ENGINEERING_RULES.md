# Engineering Rules (Constitution Technique)

> **Document annoté le 2026-07-31** sur la base de `docs/refont/AUDIT_COMPLET_2026-07-31.md` (verdict **NO-GO**).
>
> **Les six règles ne sont pas modifiées : elles sont justes.** Ce qui est ajouté, c'est leur **état de
> respect mesuré**. Une constitution technique qui ne dit pas où elle est violée ne protège rien — elle
> donne l'impression d'une protection, ce qui est pire que pas de règle du tout.
>
> **Mesure : 4 règles sur 6 sont violées** (3, 4, 5, 6). Une seule est réellement respectée (1, isolement du
> domaine). La sixième — la Règle 2 — n'est pas respectée : elle est **non vérifiable**, parce que le
> composant qu'elle encadre n'existe pas dans le dépôt.

## Objectif rappelé

**Démo réelle sur Deriv pour entraîner le système, puis capital réel.** Ces règles sont les garde-fous qui
rendent ce passage survivable. Une règle déclarée « absolue » et violée en silence est exactement le
mécanisme par lequel un compte réel se vide sans que personne ne comprenne pourquoi.

## Tableau de respect mesuré

| Règle | Énoncé | Respect mesuré | Preuve |
|---|---|---|---|
| 1 | Isolement du Domaine | **Respectée** | `domain/` n'importe que la stdlib. Seule règle tenue. |
| 2 | Aucun LLM dans le chemin critique | **Non vérifiable** | Aucun LLM n'est câblé du tout : `MockReasoner()` en production (`api/deps.py:53`). Une règle qu'on respecte par absence du composant n'est pas une règle appliquée. |
| 3 | Justification des dépendances | **Violée** | 1 532 lignes de Kronos amont vendorées dans `providers/kronos/shiyu_model/` **sans LICENSE dans le dépôt**. Aucune justification n'a été portée au `GITHUB_INTEGRATION_GUIDE.md` pour ce vendoring. |
| 4 | Validation par les tests | **Violée** | La collecte `pytest` échoue : `ModuleNotFoundError: No module named 'aegis_trade.application.council.aggregator'` (36 `__init__.py` manquants, 7 imports préfixés `src.`). Des validateurs retournent `passed=True` en dur. Des `MagicMock(spec=X)` masquent des erreurs d'arité. |
| 5 | Documentation Driven Development | **Violée** | ~30 lignes falsifiées sur 15 fichiers (§5.4 de l'audit) — c'est précisément ce que le présent chantier corrige. La doc a suivi l'intention, pas le code. |
| 6 | Traçabilité des décisions | **Violée** | La base vectorielle d'expériences n'est jamais alimentée (`MemoryManager(` : 0 occurrence). Aucune décision passée n'est rejouable. |

## Règle 1 : Isolement du Domaine (Clean Architecture)
**Aucun accès direct au Broker depuis le Domain.**
Toutes les interactions avec le marché passent par la couche Infrastructure via des Interfaces (Ports). Le Domain ne connaît pas `vn.py`, il connaît `ILiveBroker`.

## Règle 2 : Sécurisation du Chemin Critique
**Aucun LLM dans le chemin critique d'exécution.**
La décision de prendre un trade temps réel doit être millisecondée et déterministe (Vector Search FAISS, calculs statistiques). Les LLM opèrent **asynchrone** pour l'analyse post-trade, ou en parallèle pour les news.

> **Correctif de fait (2026-07-31) :** la mention de FinGPT comme exemple est retirée — FinGPT est
> `[ABANDONNÉ]` (`ADR-002`). Aucun LLM, ni FinGPT ni Ollama, n'est câblé dans le dépôt. La règle reste
> valide pour le jour où il y en aura un.

## Règle 3 : Justification des Dépendances
**Toute nouvelle dépendance doit être justifiée.**
Avant de faire un `pip install` ou de modifier le `pyproject.toml`, l'avantage comparatif doit être documenté dans le `GITHUB_INTEGRATION_GUIDE.md`. La question *"Pourquoi ne pas le réécrire nous-mêmes ?"* doit avoir une réponse solide.

> **Extension nécessaire (2026-07-31) :** cette règle ne couvre pas le **vendoring**. Copier 1 532 lignes
> de code amont dans `providers/kronos/shiyu_model/` n'est ni un `pip install` ni une modification du
> `pyproject.toml` — la règle n'a donc pas mordu, et le dépôt porte du code tiers sans LICENSE. Toute
> copie de code amont doit désormais être traitée comme une dépendance : justification **et** licence.

## Règle 4 : Validation par les Tests
**Toute stratégie doit avoir des tests.**
Un agent, un extracteur de features, ou un modèle RL ne passe jamais en production sans une suite de tests unitaires couvrant les *edge cases*.

> **Correctif de fait (2026-07-31) :** la règle dit « avoir des tests ». Insuffisant. Le dépôt **a** des
> tests ; ils ne se collectent pas, et certains passent en validant des constantes. Formulation
> renforcée : *un test qui ne s'exécute pas, ou qui affirme un résultat écrit en dur, compte comme
> absence de test.* Le Lot 0 rétablit la collecte, le Lot 4 remplace les validateurs à `passed=True`.

## Règle 5 : Documentation Driven Development
**Toute mission doit mettre à jour la documentation.**
L'architecture, les spécifications, et le logbook doivent être mis à jour *avant* le code. Le code est la traduction de la documentation, et non l'inverse.

> **Correctif de fait (2026-07-31) :** cette règle a produit l'effet inverse de celui visé. Écrire la doc
> *avant* le code est légitime, mais rien n'imposait de **revenir corriger la doc quand le code diverge**.
> Résultat mesuré : ~30 lignes déclarant « Fait », « Intégré », « Entièrement implémenté » sur 15 fichiers,
> pour du code non câblé. Complément : *toute affirmation d'état dans `docs/` doit citer un
> `fichier:ligne` vérifiable, ou porter un marqueur de statut mesurable.*

## Règle 6 : Traçabilité des Décisions
**Toute décision doit être traçable.**
Le journal des logs JSON, la base vectorielle d'expériences, et le *Research Logbook* garantissent que l'on puisse expliquer mathématiquement pourquoi Aegis a pris une position à une milliseconde donnée.

> **Correctif de fait (2026-07-31) :** aucun des trois supports cités ne contient de décision réelle. La
> base vectorielle n'est jamais écrite, et le `RESEARCH_LOGBOOK.md` ne consigne aucun trade. Prérequis :
> Lot 2 (données réelles) puis traçage `git_version` + `data_hash` sur chaque cycle.

## Ce que ce document ne promet pas

- **Pas de conformité.** Ces règles décrivent l'état visé, pas l'état du dépôt. Quatre sur six sont violées
  au 2026-07-31, une cinquième est non vérifiable.
- **Pas d'auto-application.** Aucune de ces règles n'est vérifiée par un hook, un test ou une CI. Elles
  ne tiennent que par discipline humaine — c'est exactement pour ça qu'elles ont dérivé sans alerte.
- **Une règle « absolue » n'est pas un mécanisme.** Tant que la Règle 3 n'est pas un contrôle de licence
  automatisé et la Règle 5 un test sur les affirmations de `docs/`, elles restent des intentions écrites.

