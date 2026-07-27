import itertools
from typing import Dict, Any, List, Iterator
from aegis_trade.domain.research import ExperimentConfig

class GridSearchSpace:
    """
    Génère un espace de recherche (Search Space) pour préparer le Machine Learning.
    Produit toutes les combinaisons possibles (Grid Search) de paramètres pour une stratégie.
    """
    
    def __init__(self, strategy_class_name: str, validation_config_dict: Dict[str, Any], data_sources: List[str]):
        self.strategy_class_name = strategy_class_name
        self.validation_config_dict = validation_config_dict
        self.data_sources = data_sources
        self.param_grid: Dict[str, List[Any]] = {}
        
    def add_parameter(self, param_name: str, values: List[Any]):
        """Ajoute une dimension à l'espace de recherche."""
        self.param_grid[param_name] = values
        
    def generate_configs(self) -> Iterator[ExperimentConfig]:
        """Génère toutes les configurations possibles."""
        if not self.param_grid:
            yield ExperimentConfig(
                strategy_class_name=self.strategy_class_name,
                strategy_kwargs={},
                validation_config_dict=self.validation_config_dict,
                data_sources=self.data_sources
            )
            return
            
        keys = list(self.param_grid.keys())
        value_lists = list(self.param_grid.values())
        
        for combination in itertools.product(*value_lists):
            kwargs = dict(zip(keys, combination))
            yield ExperimentConfig(
                strategy_class_name=self.strategy_class_name,
                strategy_kwargs=kwargs,
                validation_config_dict=self.validation_config_dict,
                data_sources=self.data_sources
            )
