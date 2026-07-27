import json
import logging
from pathlib import Path
from dataclasses import asdict
from typing import Optional, List
from datetime import datetime

from aegis_trade.domain.validation import ValidationArtifact

logger = logging.getLogger(__name__)

class ValidationRegistry:
    """
    Service d'historisation des campagnes de validation.
    Enregistre les ValidationArtifact sous forme de fichiers JSON pour assurer la traçabilité.
    """
    def __init__(self, registry_dir: str = ".validation_registry"):
        self.registry_dir = Path(registry_dir)
        self.registry_dir.mkdir(parents=True, exist_ok=True)
        
    def _generate_filename(self, artifact: ValidationArtifact) -> str:
        timestamp = artifact.context.timestamp.strftime("%Y%m%d_%H%M%S")
        strategy_version = artifact.context.strategy_version
        score = int(artifact.report.strategy_score)
        return f"val_{timestamp}_{strategy_version}_score_{score}.json"
        
    def save_artifact(self, artifact: ValidationArtifact) -> str:
        """Sauvegarde l'artefact complet en JSON."""
        filename = self._generate_filename(artifact)
        filepath = self.registry_dir / filename
        
        # Dataclass asdict with custom serialization for datetime/enum
        def _default_serializer(obj):
            if isinstance(obj, datetime):
                return obj.isoformat()
            if hasattr(obj, 'value'): # For Enums
                return obj.value
            return str(obj)
            
        data = asdict(artifact)
        
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, default=_default_serializer)
            logger.info(f"ValidationArtifact saved to {filepath}")
            return str(filepath)
        except Exception as e:
            logger.error(f"Failed to save ValidationArtifact: {e}")
            raise
            
    def list_artifacts(self) -> List[str]:
        """Retourne la liste des fichiers JSON du registre."""
        return [str(p) for p in self.registry_dir.glob("val_*.json")]
