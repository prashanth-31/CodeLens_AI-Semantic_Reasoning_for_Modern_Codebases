# llm_client.py
"""
Legacy HuggingFace-based LLM client.
NOTE: This project now uses OllamaClient instead. This file is kept for reference.
"""

from typing import Dict, Any, Optional
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from .config import LOCAL_MODEL_ID
from .cache import load_from_cache, save_to_cache


class LLMClient:
    """
    Local HuggingFace model with caching and optimized generation speed.
    
    Note: Consider using OllamaClient for better performance with deepseek-coder.
    """

    def __init__(self, model_id: str = LOCAL_MODEL_ID):
        """
        Initialize the LLM client with a HuggingFace model.
        
        Args:
            model_id: The HuggingFace model identifier to load.
        """
        self.model_id = model_id
        self.tokenizer = AutoTokenizer.from_pretrained(self.model_id)
        self.model = AutoModelForCausalLM.from_pretrained(
            self.model_id,
            torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
            device_map="auto" if torch.cuda.is_available() else None,
        )

    def generate(self, prompt: str, extra_params: Optional[Dict[str, Any]] = None) -> str:
        """
        Generate a response for the given prompt.
        
        Args:
            prompt: The input text to generate a response for.
            extra_params: Optional dictionary of additional generation parameters.
            
        Returns:
            The generated text response.
        """
        params = {
            "max_new_tokens": 80,
            "temperature": 0.1,
            "do_sample": False
        }

        if extra_params:
            params.update(extra_params)

        full_prompt = (
            "You are an expert Python documentation assistant. "
            "Answer concisely and clearly.\n\n"
            f"User: {prompt}\nAssistant:"
        )

        encoded = self.tokenizer(full_prompt, return_tensors="pt").to(self.model.device)

        with torch.no_grad():
            out = self.model.generate(
                **encoded,
                max_new_tokens=params["max_new_tokens"],
                temperature=params["temperature"],
                do_sample=params["do_sample"],
            )

        text = self.tokenizer.decode(out[0], skip_special_tokens=True)
        return text.split("Assistant:")[-1].strip()

    def generate_with_cache(
        self,
        prompt: str,
        cache_key_extra: Optional[Dict[str, Any]] = None,
        extra_params: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Generate a response with caching support.
        
        Args:
            prompt: The input text to generate a response for.
            cache_key_extra: Additional data to include in the cache key.
            extra_params: Optional dictionary of additional generation parameters.
            
        Returns:
            The generated (or cached) text response.
        """
        cached = load_from_cache(prompt, extra=cache_key_extra)
        if cached:
            return cached

        resp = self.generate(prompt, extra_params=extra_params)

        save_to_cache(prompt, resp, extra=cache_key_extra)
        return resp
