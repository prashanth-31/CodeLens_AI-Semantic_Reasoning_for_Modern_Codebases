# ask_cli.py
from pathlib import Path
from typing import Optional, List, Dict
from .search_index import SearchIndex
from .ollama_client import OllamaClient
from .cache import load_from_cache, save_to_cache

DEFAULT_TOP_K = 5


class CodebaseAssistant:
    """
    An intelligent assistant for answering questions about a codebase.
    Uses semantic search to find relevant code and LLM for reasoning.
    """
    
    def __init__(self, repo_path: Path, llm: Optional[OllamaClient] = None):
        self.repo_path = repo_path
        self.llm = llm or OllamaClient()
        self.index = SearchIndex()
        self.index.build_index(repo_path)
        self.conversation_history: List[Dict[str, str]] = []

    def _build_context(self, query: str, top_k: int = DEFAULT_TOP_K) -> tuple[str, list]:
        """Build context from relevant code snippets."""
        hits = self.index.query(query, top_k=top_k)
        parts = []
        sources = []
        
        for (path, name, lineno), score, snippet in hits:
            # Convert Path to string for JSON serialization
            path_str = str(path) if hasattr(path, '__fspath__') else path
            
            # Clean up snippet for better readability
            clean_snippet = snippet.strip()
            if len(clean_snippet) > 800:
                clean_snippet = clean_snippet[:800] + "\n... (truncated)"
            
            parts.append(
                f"📄 **{path_str}** → `{name}()` (line {lineno})\n"
                f"```python\n{clean_snippet}\n```"
            )
            sources.append({
                "file": path_str,
                "function": name,
                "line": lineno,
                "relevance": round(score, 3)
            })
        
        context = "\n\n".join(parts)
        return context, sources

    def _get_conversation_context(self, max_turns: int = 3) -> str:
        """Get recent conversation history for context."""
        if not self.conversation_history:
            return ""
        
        recent = self.conversation_history[-max_turns * 2:]  # Each turn has Q+A
        history_parts = []
        for msg in recent:
            role = "User" if msg["role"] == "user" else "Assistant"
            history_parts.append(f"{role}: {msg['content'][:200]}")
        
        return "\n".join(history_parts)

    def ask(
        self, 
        question: str, 
        top_k: int = DEFAULT_TOP_K,
        include_history: bool = True
    ) -> tuple[str, list]:
        """
        Ask a question about the codebase.
        
        Returns:
            Tuple of (answer, sources) where sources is a list of relevant code locations.
        """
        # Check cache first
        cache_key = f"{question}_{top_k}"
        cache_resp = load_from_cache(cache_key, extra={"repo": str(self.repo_path)})
        if cache_resp and isinstance(cache_resp, dict):
            return cache_resp.get("answer", ""), cache_resp.get("sources", [])

        # Build context from codebase
        context, sources = self._build_context(question, top_k=top_k)
        
        # Build conversation context
        conv_context = ""
        if include_history and self.conversation_history:
            conv_context = f"\n\nRecent conversation:\n{self._get_conversation_context()}\n"

        # Enhanced prompt
        prompt = f"""You are an expert code analyst helping a developer understand their Python codebase.

INSTRUCTIONS:
- Answer based ONLY on the provided code context
- Be specific: mention file names, function names, and line numbers
- If you find the answer, explain clearly with code references
- If the context doesn't contain enough info, say so honestly
- Use markdown formatting for clarity
- Keep responses focused and under 300 words

PROJECT: {self.repo_path.name}
{conv_context}
CODE CONTEXT:
{context}

QUESTION: {question}

ANSWER:"""

        # Generate response
        resp = self.llm.generate(prompt, max_tokens=400, temperature=0.2)
        
        # Store in conversation history
        self.conversation_history.append({"role": "user", "content": question})
        self.conversation_history.append({"role": "assistant", "content": resp})
        
        # Cache the response
        save_to_cache(cache_key, {"answer": resp, "sources": sources}, extra={"repo": str(self.repo_path)})
        
        return resp, sources

    def get_suggested_questions(self) -> List[str]:
        """Get suggested questions based on the codebase structure."""
        suggestions = [
            "What are the main classes in this project?",
            "How does the code parsing work?",
            "What external APIs or services does this project use?",
            "Explain the main entry points of this application",
            "What are the key functions in this codebase?",
            "How is error handling implemented?",
            "What configuration options are available?",
        ]
        return suggestions

    def clear_history(self):
        """Clear conversation history."""
        self.conversation_history = []
