import os
import json
from typing import Dict, Any

class Config:
    def __init__(self, base_path: str):
        self.config_file = os.path.join(base_path, "config.json")
        self._config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file or return defaults."""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, "r") as f:
                    return json.load(f)
            except json.JSONDecodeError:
                pass
        return {
            "ollama_url": "http://localhost:11434",
            "ollama_model": "mistral",
            "debug_enabled": False,
            "log_level": "INFO",
        }

    def save(self) -> None:
        """Save current configuration to file."""
        with open(self.config_file, "w") as f:
            json.dump(self._config, f)

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        return self._config.get(key, default)

    def set(self, key: str, value: Any) -> None:
        """Set configuration value and save."""
        self._config[key] = value
        self.save()

    def update(self, updates: Dict[str, Any]) -> None:
        """Update multiple configuration values and save."""
        self._config.update(updates)
        self.save()
