import json
import urllib.request
import urllib.parse
import urllib.error

from typing import Dict, Any

from aegis_trade.domain.reasoning import ILLMReasoner, ClusterData

class MockReasoner(ILLMReasoner):
    """
    Used for unit testing without invoking an actual LLM.
    """
    def generate_hypothesis(self, cluster: ClusterData) -> str:
        features_str = ", ".join([f"{k}: {v:.2f}" for k, v in cluster.centroid_features.items()])
        if cluster.is_success_cluster:
            return f"Success cluster found with features: {features_str}."
        else:
            return f"Failure cluster found with features: {features_str}."

class OllamaReasoner(ILLMReasoner):
    """
    Adapter for a local LLM via Ollama REST API.
    Maintains the privacy-first, local-first requirement (no Cloud LLMs).
    """
    def __init__(self, model_name: str = "llama3", base_url: str = "http://localhost:11434"):
        self.model_name = model_name
        self.base_url = base_url
        
    def generate_hypothesis(self, cluster: ClusterData) -> str:
        prompt = self._build_prompt(cluster)
        
        payload = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "temperature": 0.2  # Low temperature for analytical consistency
        }
        
        try:
            req = urllib.request.Request(
                f"{self.base_url}/api/generate",
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=30.0) as response:
                result = json.loads(response.read().decode("utf-8"))
                return result.get("response", "Could not generate hypothesis.")
        except (urllib.error.URLError, json.JSONDecodeError, TimeoutError) as e:
            # Fallback behavior if Ollama is not running or model fails
            return f"Ollama failed to generate hypothesis: {str(e)}. Centroid: {cluster.centroid_features}"
            
    def _build_prompt(self, cluster: ClusterData) -> str:
        direction = "SUCCESSFUL" if cluster.is_success_cluster else "FAILED"
        
        features_json = json.dumps(cluster.centroid_features, indent=2)
        variance_json = json.dumps(cluster.variance_features, indent=2)
        
        return f"""
You are Aegis Quant OS, an advanced institutional-grade quantitative reasoning engine.
Analyze the following cluster of {cluster.size} {direction} trades.

Centroid Features (Averages):
{features_json}

Feature Variance (Volatility within the cluster):
{variance_json}

Provide a concise, mathematical hypothesis (max 3 sentences) explaining this cluster.
Do not invent data. Focus strictly on the provided features and their relationships.
"""
