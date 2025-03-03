import json
import re
import requests
from app.schemas import SecurityAnalysis, IOC


class LLMService:
    def __init__(self, base_url="http://ollama:11434", model="mistral"):
        self.base_url = base_url
        self.model = model

    def get_available_models(self) -> list[str]:
        """Get list of available models from Ollama."""
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            response.raise_for_status()
            return [model["name"] for model in response.json()["models"]]
        except (requests.RequestException, KeyError) as e:
            print(f"Error getting models: {str(e)}")
            return ["mistral"]  # Return default model as fallback

    def _filter_thinking_tags(self, text: str) -> str:
        """Remove content between <think> and </think> tags."""
        return re.sub(r'<think>.*?</think>', '', text, flags=re.DOTALL)

    def _generate(self, prompt: str, format_schema: dict = None) -> str:
        try:
            request_data = {"model": self.model, "prompt": prompt, "stream": False}
            if format_schema:
                request_data["format"] = format_schema

            response = requests.post(
                f"{self.base_url}/api/generate",
                json=request_data,
                timeout=30,
            )
            response.raise_for_status()
            response_text = response.json()["response"]
            
            # Filter thinking tags if using a thinking model
            if any(model in self.model.lower() for model in ["deepseek", "yi"]):
                response_text = self._filter_thinking_tags(response_text)
                
            return response_text
        except (requests.RequestException, KeyError) as e:
            return f"Error generating response: {str(e)}"

    def update_config(self, base_url: str, model: str) -> None:
        """Update the LLM service configuration."""
        self.base_url = base_url
        self.model = model

    def summarize_article(self, content: str) -> str:
        prompt = f"""Summarize the following article concisely in 2-3 sentences, only reply with the summary.:

{content}

Summary:"""
        return self._generate(prompt)

    def analyze_detailed_content(self, content: str) -> str:
        prompt = f"""Analyze the following article in detail. Include:
1. Key points and findings
2. Technical details if present
3. Impact assessment
4. Related technologies/concepts mentioned
5. Any recommendations or conclusions

{content}

Analysis:"""
        return self._generate(prompt)

    def analyze_security_content(self, content: str) -> tuple[list, str]:
        # Create prompt for structured IOC extraction
        ioc_prompt = f"""Extract potential Indicators of Compromise (IOCs) from the following security article and create a Sigma rule.

Article:
{content}

Instructions:
1. Identify all potential IOCs (IPs, domains, URLs, file hashes)
2. For each IOC:
   - Determine the correct type (ip, domain, hash, url)
   - Extract the value
   - Include surrounding context
   - Assess confidence level (1-100)
3. Create a Sigma rule if applicable

Your response should be a structured output with:
- A list of IOCs including type, value, context, and confidence
- A Sigma rule (or null if not applicable)"""

        # Use Pydantic model schema for structured output
        analysis_schema = SecurityAnalysis.model_json_schema()

        # Get structured response and filter thinking tags before JSON parsing
        response = self._generate(ioc_prompt, format_schema=analysis_schema)
        try:
            # Filter thinking tags while preserving JSON structure
            if any(model in self.model.lower() for model in ["deepseek", "yi"]):
                response = self._filter_thinking_tags(response)
            analysis = SecurityAnalysis.model_validate_json(response)
            return (
                analysis.iocs,
                analysis.sigma_rule or "No applicable Sigma rule for this content.",
            )
        except Exception as e:
            print(f"Error parsing structured response: {str(e)}")
            return [], "Error generating Sigma rule"
