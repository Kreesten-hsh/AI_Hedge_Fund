# Critères de Sortie & Protocole de Validation Démo V2.0

- **Statut** : SPÉCIFICATION TECHNIQUE V2.0 (Lot 1)
- **Date** : 2026-08-08
- **Composants concernés** : `docs/RAG_LEARNING_LOOP_SPEC.md`, `src/aegis_trade/domain/trade_record.py`, `scripts/verify_demo_exit.py`
- **Dépend de** : ADR 0014 (Paper Trading Before Live), ADR 0032 (Pivot Pipeline Cognitif v2.0)

---

## 1. Conditions Cumulatives de Sortie de Démo

Pour que le prototype du Pipeline Cognitif Sémantique v2.0 soit déclaré **VALIDE** et éligible au passage en phase suivante (Lot 2 / Phase de déploiement), il doit satisfaire **simultanément et sans exception** aux deux conditions statistiques cumulatives suivantes :

### Condition 1 : Taille d'Échantillon ($N \ge 100$)
- **Seuil** : Au moins **100 trades uniques** doivent être enregistrés et clôturés dans le journal d'expérience RAG (`FaissVectorStore` / `MemoryEntry`).
- **Périmètre** : Environnement de simulation réaliste (`SimulatedBroker`) ou Paper Trading (`DerivGateway`) avec déduction obligatoire et réelle des péages d'exécution ($1.859\text{ bps}$ Or, $10\text{ bps}$ Crypto).

### Condition 2 : Profit Factor ($\text{PF} \ge 1.50$)
- **Définition** : Ratio des gains bruts cumulés sur les pertes brutes cumulées sur l'échantillon complet des $N \ge 100$ trades :
  $$\text{Profit Factor} = \frac{\sum \text{Gross Profit}}{\sum \text{Gross Loss}} \ge 1.50$$
- **Seuil** : Le Profit Factor doit être **strictement supérieur ou égal à 1.50** sur l'échantillon global hors tout biais de sélection post-hoc.

---

## 2. Mécanisme de Vérification Automatisé

> [!IMPORTANT]
> **Interdiction du contrôle manuel occasionnel** : La validation des critères de sortie ne repose jamais sur une vérification manuelle ou visuelle occasionnelle. Elle est effectuée exclusivement par un script automatisé déterministe.

### Script de Vérification Automatisé (`scripts/verify_demo_exit.py`)

Un script d'audit autonome interroge directement le journal de mémoire RAG et la base de données des trades pour calculer les métriques réelles.

```python
# Exemple de logique d'audit automatisé (scripts/verify_demo_exit.py)
import sys
import json
from pathlib import Path

def verify_demo_exit(journal_path: Path) -> bool:
    with open(journal_path, "r") as f:
        trades = [json.loads(line) for line in f]
    
    n_trades = len(trades)
    if n_trades < 100:
        print(f"❌ ÉCHEC: Nombre de trades insuffisant N = {n_trades} < 100")
        return False
        
    gross_profit = sum(t["outcome"]["net_pnl_pct"] for t in trades if t["outcome"]["net_pnl_pct"] > 0)
    gross_loss = abs(sum(t["outcome"]["net_pnl_pct"] for t in trades if t["outcome"]["net_pnl_pct"] < 0))
    
    pf = gross_profit / gross_loss if gross_loss > 0 else float("inf")
    
    print(f"📊 Bilan Démo: N = {n_trades} trades | Profit Factor = {pf:.2f}")
    
    if pf >= 1.50:
        print("✅ SUCCÈS: Critères de sortie démo validés!")
        return True
    else:
        print(f"❌ ÉCHEC: Profit Factor {pf:.2f} < 1.50")
        return False

if __name__ == "__main__":
    success = verify_demo_exit(Path("user_data/memory/trade_journal.jsonl"))
    sys.exit(0 if success else 1)
```

---

## 3. Matrice de Décision Post-Validation

| Nombre de Trades ($N$) | Profit Factor ($\text{PF}$) | Statut de la Démo | Action Recommandée |
| :--- | :--- | :--- | :--- |
| $< 100$ | N/A | **INCOMPLET** | Poursuivre le déroulement des sessions démo jusqu'à $N=100$. |
| $\ge 100$ | $< 1.50$ | **ÉCHEC / REJET** | Pipeline cognitif réfuté. Ouverture d'un audit de prompt / RAG. |
| $\ge 100$ | $\ge 1.50$ | **SUCCÈS / VALIDÉ** | Scellement de la démo v2.0 et déblocage du Lot 2 (Roadmap & Dashboard). |
