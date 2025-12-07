# search_index.py
from pathlib import Path
from typing import List, Tuple
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import linear_kernel
from .code_parser import extract_functions_from_file


class SearchIndex:
    def __init__(self):
        self.vectorizer = TfidfVectorizer(
            input="content", analyzer="word", ngram_range=(1, 2), max_features=20000
        )
        self.docs = []
        self.metadata = []
        self.tfidf = None

    def build_index(self, repo_path: Path):
        self.docs = []
        self.metadata = []
        for py in repo_path.rglob("*.py"):
            if not py.is_file():
                continue
            try:
                funcs = extract_functions_from_file(py)
            except Exception:
                text = py.read_text(encoding="utf-8")
                self.docs.append(text)
                self.metadata.append((py, "<module>", 1))
                continue

            for f in funcs:
                snippet = f"# File: {py}\n# Function: {f.name}\n\n" + (f.code or "")
                self.docs.append(snippet)
                self.metadata.append((py, f.name, f.lineno))

        if not self.docs:
            self.tfidf = None
            return

        self.tfidf = self.vectorizer.fit_transform(self.docs)

    def query(self, q: str, top_k: int = 5) -> List[Tuple[Tuple[Path, str, int], float, str]]:
        if self.tfidf is None or not self.docs:
            return []
        q_vec = self.vectorizer.transform([q])
        cosine_similarities = linear_kernel(q_vec, self.tfidf).flatten()
        ranked_idx = cosine_similarities.argsort()[::-1][:top_k]
        results = []
        for idx in ranked_idx:
            md = self.metadata[idx]
            score = float(cosine_similarities[idx])
            snippet = self.docs[idx]
            results.append((md, score, snippet))
        return results
