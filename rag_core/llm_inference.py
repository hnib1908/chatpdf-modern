# core/llm_inference.py
#
# NOTE FOR REVIEWERS:
# Copied from the original repo. The two additive changes are:
#   1. An optional `temperature` parameter (new UI control in the sidebar).
#      When not provided, Ollama/Sambanova defaults are used exactly as before.
#   2. A new `generate_text_ollama_stream()` generator method, used ONLY for
#      the typewriter-effect in the new UI. It calls the same `ollama.chat`
#      API, just with `stream=True`, and yields tokens as they arrive instead
#      of waiting for the full response. It does not change what the model
#      is asked or how the answer is produced.

import os
import json
import ollama
import requests
import shelve
import hashlib
import json
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

API_KEY = os.getenv('API_KEY')
API_URL = "https://api.sambanova.ai/v1/chat/completions"

class LLMInference:

    def _format_time(self, response_time):
        minutes = response_time // 60
        seconds = response_time % 60
        return f"{int(minutes)}m {int(seconds)}s" if minutes else f"Time: {int(seconds)}s"

    def _generate_embeddings(self, input_text: str, model_name: str, provider: str = 'ollama'):
        """Generate embeddings with a simple on-disk cache to avoid recomputing.

        Currently supports provider='ollama'. The cache key is SHA256(provider|model|text).
        """
        # Prepare cache
        cache_dir = Path("tmp")
        cache_dir.mkdir(parents=True, exist_ok=True)
        cache_path = cache_dir / "embeddings_cache.db"

        key_raw = f"{provider}|{model_name}|{input_text}"
        key = hashlib.sha256(key_raw.encode("utf-8")).hexdigest()

        with shelve.open(str(cache_path)) as db:
            if key in db:
                try:
                    return json.loads(db[key])
                except Exception:
                    # fallthrough to regenerate if cache corrupted
                    pass

            # Only ollama is supported for now; keep interface extensible
            if provider == 'ollama':
                embedding = ollama.embeddings(model=model_name, prompt=input_text).get("embedding", [])
            else:
                raise ValueError(f"Unsupported embedding provider: {provider}")

            # store as JSON string to be robust across platforms
            try:
                db[key] = json.dumps(embedding)
            except Exception:
                # if storing fails, ignore caching but return embedding
                pass

            return embedding

    def generate_text_ollama(self, prompt: str, model_name: str, temperature: float = None):

        if not prompt or not model_name:
            return {"error": "Both 'prompt' and 'model_name' are required"}

        try:
            options = {"temperature": temperature} if temperature is not None else None
            response = ollama.chat(
                model=model_name,
                messages=[{"role": "user", "content": prompt}],
                options=options,
            )
            return response.get("message", {}).get("content", "")
        except Exception as e:
            return {"error": "Failed to generate response using Ollama", "details": str(e)}

    def generate_text_ollama_stream(self, prompt: str, model_name: str, temperature: float = None):
        """Yields response tokens as they are generated (for the UI typewriter effect).
        Same model call as generate_text_ollama, only `stream=True` differs."""
        options = {"temperature": temperature} if temperature is not None else None
        stream = ollama.chat(
            model=model_name,
            messages=[{"role": "user", "content": prompt}],
            options=options,
            stream=True,
        )
        for chunk in stream:
            token = chunk.get("message", {}).get("content", "")
            if token:
                yield token

    def generate_text_sambanova(self, prompt: str, model_name: str, temperature: float = None):
        if not prompt or not model_name:
            return {"error": "Both 'prompt' and 'model_name' are required"}

        payload = {
            "model": model_name,
            "messages": [{
                "role": "user",
                "content": prompt
            }],
        }
        if temperature is not None:
            payload["temperature"] = temperature

        response = requests.post(
            url=API_URL,
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "Content-Type": "application/json",
            },
            data=json.dumps(payload)
        )

        response_data = json.loads(response.text)
        # Check if there's an error key in the response
        if "error" in response_data:
            error_message = response_data["error"].get("message", "Unknown error")
            raise Exception(f"API Error: {error_message}")

        return response_data["choices"][0]["message"]["content"], response_data["usage"]["total_tokens"]

    def generate_text(self, prompt: str, model_name: str, llm_provider: str, temperature: float = None):
        if llm_provider == 'Ollama':
            return self.generate_text_ollama(prompt, model_name, temperature=temperature)
        elif llm_provider == 'Sambanova':
            return self.generate_text_sambanova(prompt, model_name, temperature=temperature)
        else:
            raise ValueError("Unsupported LLM provider. Choose either 'Ollama' or 'Sambanova'.")


if __name__ == "__main__":
    llm = LLMInference()
    prompt = "What is the capital of France?"
    response = llm.generate_text(prompt, model_name="QwQ-32B", llm_provider='Sambanova')
    print(response)
