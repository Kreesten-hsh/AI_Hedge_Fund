import json
import os
from dataclasses import asdict
from typing import Optional

from aegis_trade.domain.research import AlphaResearchResult

class ResearchReport:
    """
    Generates and saves JSON reports from Alpha Research evaluations.
    """

    @staticmethod
    def generate_json(result: AlphaResearchResult, filepath: Optional[str] = None) -> str:
        """
        Converts an AlphaResearchResult into a JSON string and optionally saves it.
        
        Args:
            result: The AlphaResearchResult containing rankings and metrics.
            filepath: Optional path to save the JSON file (e.g. data/reports/...).
            
        Returns:
            The JSON string representation of the report.
        """
        # Convert dataclasses to dict using standard asdict
        # We need to handle datetime serialization
        def _default_encoder(obj):
            if hasattr(obj, 'isoformat'):
                return obj.isoformat()
            if hasattr(obj, 'value') and type(obj).__name__ in ('Symbol', 'TimeFrame'):
                return obj.value
            return str(obj)

        # Convert symbol to string directly as it might be a dataclass itself depending on domain.core
        # Actually, let's just build a safe dict.
        data = asdict(result)
        
        json_str = json.dumps(data, default=_default_encoder, indent=4)
        
        if filepath:
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            with open(filepath, 'w') as f:
                f.write(json_str)
                
        return json_str
