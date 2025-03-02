import json
import requests

class LLMService:
    def __init__(self, base_url="http://ollama:11434"):
        self.base_url = base_url

    def _generate(self, model: str, prompt: str) -> str:
        response = requests.post(
            f"{self.base_url}/api/generate",
            json={
                "model": model,
                "prompt": prompt,
                "stream": False
            }
        )
        return response.json()["response"]

    def summarize_article(self, content: str) -> str:
        prompt = f"""Summarize the following article concisely in 2-3 sentences:

{content}

Summary:"""
        return self._generate("mistral", prompt)

    def analyze_security_content(self, content: str) -> tuple[list, str]:
        # Extract IOCs
        ioc_prompt = f"""Extract potential Indicators of Compromise (IOCs) from the following security article. 
Return the result as a JSON array with objects containing 'type' (ip, domain, hash, url) and 'value'.
If no IOCs are found, return an empty array.

{content}

IOCs:"""
        
        iocs_result = self._generate("mistral", ioc_prompt)
        try:
            iocs = json.loads(iocs_result)
        except json.JSONDecodeError:
            iocs = []

        # Generate Sigma rule
        sigma_prompt = f"""Based on the following security article, create a Sigma rule that could detect the described threat.
If no meaningful detection rule can be created, return "No applicable Sigma rule for this content."

{content}

Sigma rule:"""
        
        sigma_rule = self._generate("mistral", sigma_prompt)
        
        return iocs, sigma_rule
