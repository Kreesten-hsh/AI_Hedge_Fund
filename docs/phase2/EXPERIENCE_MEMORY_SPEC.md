# Spécification de la Mémoire d'Expérience (Experience Memory)

Le système stocke non seulement des prix, mais le *contexte absolu* d'une prise de décision et de son résultat.

## 1. Architecture de l'Experience Memory
L'apprentissage s'enrichit de l'exhaustivité des spectres de marché.

```text
Experience Memory
│
├── Success Memory     (Gains clairs, exécution parfaite)
├── Failure Memory     (Pertes lourdes, règles violées)
├── Near Miss Memory   (Presque bons/mauvais : TP frôlé, SL frôlé de 1 pip)
├── Exceptional Memory (Cygnes noirs, annonces macro extrêmes, flash crash)
└── Unknown Memory     (Situations de marché jamais vues, incertitude mathématique)
```

- **Success Memory** : Base vectorielle isolée contenant les trades ayant généré un PnL positif avec un rapport Gain/Risque satisfaisant.
- **Failure Memory** : Base vectorielle des désastres. Apprentissage de l'évitement.
- **Near Miss Memory** : Crucial pour optimiser le slippage et le placement de Take Profit/Stop Loss.
- **Exceptional Memory** : Préserve le capital lors de conditions rares qui feraient exploser un algo classique.
- **Unknown Memory** : Flagué quand la recherche FAISS ne trouve rien de pertinent (Score de similarité très bas). Active le mode "Risk Reduction".

## 2. Le Schéma de l'Embedding (Feature Engineering)
Toutes les features définies dans le document `FEATURE_ENGINEERING.md` sont normalisées en un vecteur `V`.

## 3. Politique de Recherche (Similarity Search)
Avant chaque exécution potentielle, le système calcule le vecteur `V_current` de l'état actuel du marché.
Il interroge FAISS (K-Nearest Neighbors) pour extraire `Top(200)` à travers toutes les dimensions mémorielles.

## 4. Politique de Stockage
Le stockage est asynchrone post-trade. Il ne ralentit pas le flux d'ordres en temps réel. Les vecteurs sont flushés sur le disque toutes les 5 minutes pour persistance locale.
