# Spécification du Multi-Agent Council

L'IA n'est pas monolithique. C'est un comité de fonctions spécialisées débattant avant validation.

## 1. Les Rôles
1. **L'Initiateur (Quant Agent)** : Détecte un motif mathématique de rupture. Propose l'ordre d'achat/vente.
2. **Le Conseiller Historique (Memory Agent)** : Reçoit la proposition, la confronte aux FAISS `Success Memory` et `Failure Memory`. 
3. **L'Analyste Macro (Context Agent)** : Évalue les conditions de liquidité globales et la volatilité.
4. **Le Risk Manager (Déterministe)** : Le juge final. Ne consulte pas d'IA. Il évalue la taille de position, l'exposition et le drawdown actuel du portefeuille.

## 2. Protocole de Vote
- Le **Quant Agent** émet un ticket de trade `T`.
- Le **Memory Agent** retourne un score de similarité `[ -100 ; +100 ]` basé sur les 200 expériences passées. 
- Si Score < 0, le trade est annulé silencieusement (Machine Learning par exclusion).
- Si Score >= 0, l'**Analyste Macro** valide le spread/liquidité.

## 3. Le Droit de Veto
Le **Risk Manager** possède le droit de VETO absolu. Même si le score mémoriel est de +100, si la taille du trade expose le compte au-delà de 2% de risque ruine, l'ordre est rejeté.

## 4. Gestion des Désaccords
Si le Memory Agent trouve 50 succès similaires et 50 échecs similaires (incertitude maximale), le système adopte un comportement de **réduction de risque** :
- Soit le trade est abandonné.
- Soit sa taille (lot) est divisée par 4.
