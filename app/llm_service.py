import json
import requests

class LLMService:
    def __init__(self, base_url="http://ollama:11434", model="mistral"):
        self.base_url = base_url
        self.model = model

    def get_available_models(self) -> list[str]:
        """Get list of available models from Ollama."""
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            return [model['name'] for model in response.json()['models']]
        except (requests.RequestException, KeyError) as e:
            print(f"Error getting models: {str(e)}")
            return ["mistral"]  # Return default model as fallback

    def _generate(self, prompt: str) -> str:
        try:
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False
                },
                timeout=30
            )
            response.raise_for_status()
            return response.json()["response"]
        except (requests.RequestException, KeyError) as e:
            return f"Error generating response: {str(e)}"

    def update_config(self, base_url: str, model: str) -> None:
        """Update the LLM service configuration."""
        self.base_url = base_url
        self.model = model

    def summarize_article(self, content: str) -> str:
        prompt = f"""Summarize the following article concisely in 2-3 sentences:

{content}

Summary:"""
        return self._generate(prompt)

    def analyze_security_content(self, content: str) -> tuple[list, str]:
        # Extract IOCs
        ioc_prompt = f"""Extract potential Indicators of Compromise (IOCs) from the following security article. 
Return the result as a JSON array with objects containing 'type' (ip, domain, hash, url) and 'value'.
If no IOCs are found, return an empty array.

{content}

IOCs:"""
        
        iocs_result = self._generate(ioc_prompt)
        try:
            iocs = json.loads(iocs_result)
        except json.JSONDecodeError:
            iocs = []

        # Generate Sigma rule
        sigma_prompt = f"""Based on the following security article, create a Sigma rule that could detect the described threat.
Include title, description, status, level, and detection sections in YAML format.
If no meaningful detection rule can be created, return "No applicable Sigma rule for this content."

{content}

Sigma rule:"""
        
        sigma_rule = self._generate(sigma_prompt)
        
        return iocs, sigma_rule
