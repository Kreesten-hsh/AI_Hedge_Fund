import json
import urllib.request
import urllib.error
from typing import Dict, Any

from aegis_trade.infrastructure.llm.adapters.base import ILLMProvider
from aegis_trade.infrastructure.llm.settings import LLMSettings

class OllamaAdapter(ILLMProvider):
    """
    Adapter for a local Ollama server, adhering to ILLMProvider interface.
    """
    
    def __init__(self, settings: LLMSettings, host: str = "http://127.0.0.1:11434"):
        self.settings = settings
        self.host = host
        self.generate_url = f"{self.host}/api/generate"

    def generate(self, prompt: str, system_prompt: str = "") -> str:
        """
        Send a generation request to the Ollama server.
        Uses settings to determine model, format, keep_alive, etc.
        """
        payload = {
            "model": self.settings.model,
            "prompt": prompt,
            "stream": False,
            "keep_alive": f"{self.settings.keep_alive}m",
            "options": {
                "temperature": self.settings.temperature
            }
        }
        
        if system_prompt:
            payload["system"] = system_prompt
            
        if self.settings.format == "json":
            payload["format"] = "json"

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(self.generate_url, data=data, headers={"Content-Type": "application/json"})
        
        try:
            with urllib.request.urlopen(req, timeout=self.settings.timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
                return result.get("response", "")
        except urllib.error.URLError as e:
            raise RuntimeError(f"Ollama connection error: {e}")
