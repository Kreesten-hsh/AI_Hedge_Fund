import logging
from typing import Iterable, Dict, Any, List
from datetime import datetime

from aegis_trade.domain.features import FeatureSet

logger = logging.getLogger(__name__)

class QlibDataset:
    """
    Encapsulation du format de données attendu par les modèles ML.
    (Normalement TSDatasetH dans Microsoft Qlib)
    """
    def __init__(self, data: List[Dict[str, Any]], target_col: str = "target"):
        self._data = data
        self.target_col = target_col
        
    @property
    def raw_data(self) -> List[Dict[str, Any]]:
        return self._data
        
    def __len__(self) -> int:
        return len(self._data)


class DatasetBuilder:
    """
    Anti-Corruption Layer : Construit un Dataset Qlib depuis le Feature Store d'Aegis.
    Le Feature Store reste l'unique source de vérité. Aucune feature n'est calculée ici.
    """
    
    def __init__(self, target_feature: str = "label_return"):
        """
        :param target_feature: Nom de la feature servant de variable cible (Y).
        """
        self.target_feature = target_feature
        
    def build_from_features(self, feature_sets: Iterable[FeatureSet]) -> QlibDataset:
        """
        Transforme un flux de FeatureSet en QlibDataset (format tabulaire).
        """
        logger.info(f"Building dataset from FeatureSets. Target: {self.target_feature}")
        
        data_rows = []
        for fset in feature_sets:
            # Flatten features
            row = {
                "symbol": fset.symbol,
                "timestamp": fset.timestamp.isoformat(),
                "timeframe": fset.timeframe.value
            }
            # Injecter toutes les features et le label
            for feat_name, feat_val in fset.features.items():
                row[feat_name] = feat_val
                
            data_rows.append(row)
            
        dataset = QlibDataset(data=data_rows, target_col=self.target_feature)
        logger.info(f"Dataset built with {len(dataset)} rows.")
        return dataset
