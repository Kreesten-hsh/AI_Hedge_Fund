from typing import Protocol, Sequence, Any

from aegis_trade.domain import DataColumn, DatasetLineage

class ReadOnlyDataset(Protocol):
    """
    Interface abstraite pour un dataset en lecture seule.
    Protège les données sous-jacentes contre les modifications et fournit un accès unifié.
    """
    def column(self, name: str) -> DataColumn:
        """Retourne une DataColumn par son nom. Lève ValueError si non trouvée."""
        ...
        
    def exists(self, name: str) -> bool:
        """Vérifie si une colonne existe."""
        ...
        
    def get_column_names(self) -> Sequence[str]:
        """Retourne la liste des noms de colonnes disponibles."""
        ...

    def row_count(self) -> int:
        """Retourne le nombre de lignes dans le dataset."""
        ...

    def metadata(self) -> dict[str, Any]:
        """Retourne les métadonnées globales du dataset."""
        ...
        
    def lineage(self) -> DatasetLineage | None:
        """Retourne l'historique (lineage) de ce dataset, si disponible."""
        ...
