# Carte de démarrage — écosystème open source quant/trading/ML

Point de départ pour accélérer l'étape 2 du processus oss-first, pas une
liste figée. Statut vérifié indiqué par entrée — à revérifier si l'entrée
n'a pas été confirmée dans les 6 derniers mois.

## Indicateurs techniques
- **pandas-ta-classic** [NON vérifié 05/08/2026 — recherche web sans résultat] — mentionné comme fork communautaire actif de pandas-ta (l'original, twopirllc, affiche lui-même un risque d'arrêt faute de soutien). Décrit comme 193+ indicateurs, 62 patterns de chandeliers, aucune dépendance TA-Lib requise, accélération optionnelle via numba (6-230× sur les indicateurs coûteux — pertinent vu le CPU dual-core). Candidat potentiel pour remplacer utils/math.py MAIS nécessite vérification GitHub (dernière activité, mainteneurs, licence) avant usage.
- TA-Lib (C, wrapper Python) — plus rapide en théorie, mais dépendance compilée, à peser contre la contrainte matérielle. Non revérifié aujourd'hui pour l'état de maintenance actuel.

## Analyse de facteurs / IC
- **alphalens-reloaded** [vérifié 05/08/2026 — [stefan-jansen/alphalens-reloaded](https://github.com/stefan-jansen/alphalens-reloaded)] — maintenu par Stefan Jansen (écosystème ml4trading), successeur actif d'alphalens (Quantopian, abandonné). Rendements par quantile, IC, turnover, tear sheets. CI active (GitHub Actions récent), compatible NumPy 2.x / pandas 2.x. Candidat direct pour research_engine.py — vérifier si nos besoins spécifiques (n_eff sur rendements chevauchants, gate de significativité) sont déjà couverts nativement avant de décider wrapper vs remplacement complet.

## Backtesting
- vectorbt, backtrader, zipline-reloaded, nautilus_trader — connus mais NON revérifiés aujourd'hui (statut de maintenance, activité récente, adéquation avec le Backtester déjà écrit et testé). Ne pas les considérer comme confirmés avant recherche dédiée le jour où ce chantier s'ouvre.

## Analyse de portefeuille / risque
- pyfolio-reloaded, quantstats, riskfolio-lib, mlfinlab/mlfinpy (code du livre de Marcos López de Prado) — connus mais NON revérifiés aujourd'hui.

## Validation de données
- pandera, great_expectations — pertinent pour la robustesse de l'ingestion (DerivHistoricalData, openbb_provider) — NON revérifiés aujourd'hui.

## RL pour le trading
- FinRL — déjà utilisé dans ce projet (AI-04). Pas de raison de le remettre en question sans motif précis.

## Note de méthode
Cette carte accélère la recherche, elle ne la remplace pas. Une entrée "vérifiée" aujourd'hui peut être fausse dans 6 mois — un mainteneur peut abandonner un projet du jour au lendemain (cf. pandas-ta lui-même). Toujours repasser par l'étape 2 du processus oss-first avant de décider.
