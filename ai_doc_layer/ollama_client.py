# ollama_client.py
import os
from typing import Optional, Dict, Any
import requests

DEFAULT_OLLAMA_URL = "http://localhost:11434"
DEFAULT_MODEL = "deepseek-coder:6.7b"


class OllamaClient:

    def __init__(
        self,
        base_url: Optional[str] = None,
        model: str = DEFAULT_MODEL,
    ):
        self.base_url = base_url or os.getenv("OLLAMA_HOST", DEFAULT_OLLAMA_URL)
        self.model = model

    def generate(
        self,
        prompt: str,
        temperature: float = 0.2,
        max_tokens: int = 2048,
        system_instruction: Optional[str] = None,
    ) -> str:
        url = f"{self.base_url}/api/generate"

        full_prompt = prompt
        if system_instruction:
            full_prompt = f"{system_instruction}\n\n{prompt}"

        payload: Dict[str, Any] = {
            "model": self.model,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens,
            },
        }

        resp = requests.post(url, json=payload, timeout=300)
        resp.raise_for_status()

        data = resp.json()
        return data.get("response", "").strip()

    def analyze_impact(
        self,
        changed_code: str,
        downstream_snippets: list[tuple[str, str, str]],
        diff_context: str = "",
    ) -> str:
        downstream_text = "\n\n".join(
            f"### {fname} :: {func}\n```python\n{code}\n```"
            for fname, func, code in downstream_snippets
        )

        prompt = f"""You are a senior software engineer performing a semantic code review.

A developer has made the following change:

```python
{changed_code}
```

{f"Git diff context:\n```diff\n{diff_context}\n```" if diff_context else ""}

The following functions/code depend on or call the changed code:

{downstream_text}

Analyze the impact of this change:

1. **Breaking Changes**: Could any downstream code break due to changed return types, parameter semantics, or side-effects?
2. **Semantic Drift**: Are there assumptions in downstream code that may now be violated?
3. **Edge Cases**: What new edge cases might be introduced?
4. **Risk Score**: Rate the risk (Low / Medium / High / Critical) with justification.
5. **Suggested Tests**: Propose specific test cases to validate correctness.
6. **Recommendations**: Any refactoring or documentation suggestions.

Be specific. Cite function names and line-level concerns where possible.
"""
        system = (
            "You are an expert code reviewer specializing in detecting subtle semantic bugs, "
            "behavioral regressions, and API contract violations in Python codebases."
        )
        return self.generate(prompt, system_instruction=system, max_tokens=3000)


GeminiClient = OllamaClient
