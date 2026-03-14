"""Token Budget Manager - Handles LLM token counting, cost tracking, and model tiering."""

import tiktoken
import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime, timedelta
import os
import re
logger = logging.getLogger(__name__)

from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure API keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
@dataclass
class TokenBudget:
    """Tracks token usage and costs for LLM calls."""
    
    # Model pricing (per 1M tokens)
    MODEL_PRICING = {
        "gemini-flash": {"input": 0.075, "output": 0.30},   # Approximate
        "gemini-pro": {"input": 0.50, "output": 1.50},
        "gpt-4": {"input": 10.00, "output": 30.00},
        "gpt-4-turbo": {"input": 10.00, "output": 30.00},
        "claude-3-haiku": {"input": 0.25, "output": 1.25},
        "claude-3-sonnet": {"input": 3.00, "output": 15.00},
        "claude-3-opus": {"input": 15.00, "output": 75.00},
    }
    
    # Model context windows
    MODEL_CONTEXT = {
        "gemini-flash": 128000,
        "gemini-pro": 128000,
        "gpt-4": 8192,
        "gpt-4-turbo": 128000,
        "claude-3-haiku": 200000,
        "claude-3-sonnet": 200000,
        "claude-3-opus": 200000,
    }
    
    # Token to character ratio (approximate)
    CHARS_PER_TOKEN = 4
    
    budget_limit: float = 5.0  # Maximum budget in USD
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    calls: List[Dict] = field(default_factory=list)
    
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count from text."""
        # Rough estimate: 1 token ≈ 4 characters
        return len(text) // self.CHARS_PER_TOKEN
    
    def count_tokens(self, text: str, model: str = "gpt-4") -> int:
        """Count tokens accurately using tiktoken if available."""
        try:
            # Try to use tiktoken for accurate counting
            encoding = tiktoken.get_encoding("cl100k_base")
            return len(encoding.encode(text))
        except:
            # Fallback to estimation
            return self.estimate_tokens(text)
    
    def can_fit_in_context(self, text: str, model: str) -> bool:
        """Check if text fits in model's context window."""
        tokens = self.count_tokens(text, model)
        max_tokens = self.MODEL_CONTEXT.get(model, 8192)
        return tokens < max_tokens
    
    def select_model(self, text: str, task: str) -> str:
        """Select appropriate model based on task, text size, and available API keys."""
        tokens = self.count_tokens(text)
        
        # Task-based model selection with API key availability check
        if task == "bulk_summary":
            # Use Gemini Flash if available (cheapest)
            if GOOGLE_API_KEY and tokens < self.MODEL_CONTEXT["gemini-flash"]:
                return "gemini-flash"  # Will map to models/gemini-1.5-flash
            elif OPENAI_API_KEY:
                return "gpt-3.5-turbo"  # Fallback to cheaper OpenAI model
            else:
                raise ValueError("No API keys available for bulk summarization")
                
        elif task == "synthesis":
            # Use best model for synthesis, but check budget and availability
            if self.total_cost() < self.budget_limit * 0.7:
                if OPENAI_API_KEY:
                    return "gpt-3.5-turbo"  # Will map to gpt-4-turbo-preview
                elif GOOGLE_API_KEY:
                    return "gemini-pro"
            else:
                if GOOGLE_API_KEY:
                    return "gemini-flash"
                elif OPENAI_API_KEY:
                    return "gpt-3.5-turbo"
            raise ValueError("No API keys available for synthesis")
    
    def track_call(self, model: str, input_tokens: int, output_tokens: int, task: str):
        """Track an LLM call for budget management."""
        self.total_input_tokens += input_tokens
        self.total_output_tokens += output_tokens
        
        self.calls.append({
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "task": task,
            "cost": self.calculate_cost(model, input_tokens, output_tokens)
        })
        
        logger.info(f"LLM Call - Model: {model}, Input: {input_tokens}, Output: {output_tokens}, Task: {task}")
        logger.info(f"Total cost so far: ${self.total_cost():.4f}")
    
    def calculate_cost(self, model: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost for a model call."""
        pricing = self.MODEL_PRICING.get(model, {"input": 0.50, "output": 1.50})
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]
        return input_cost + output_cost
    
    def total_cost(self) -> float:
        """Get total cost of all calls."""
        return sum(call["cost"] for call in self.calls)
    
    def remaining_budget(self) -> float:
        """Get remaining budget."""
        return self.budget_limit - self.total_cost()
    
    def within_budget(self) -> bool:
        """Check if we're within budget."""
        return self.total_cost() < self.budget_limit
    
    def get_summary(self) -> Dict:
        """Get budget summary."""
        return {
            "total_cost": self.total_cost(),
            "budget_limit": self.budget_limit,
            "remaining": self.remaining_budget(),
            "total_input_tokens": self.total_input_tokens,
            "total_output_tokens": self.total_output_tokens,
            "total_calls": len(self.calls),
            "calls_by_model": self._group_calls_by_model(),
        }
    
    def _group_calls_by_model(self) -> Dict:
        """Group calls by model."""
        groups = {}
        for call in self.calls:
            model = call["model"]
            if model not in groups:
                groups[model] = {
                    "count": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cost": 0.0
                }
            groups[model]["count"] += 1
            groups[model]["input_tokens"] += call["input_tokens"]
            groups[model]["output_tokens"] += call["output_tokens"]
            groups[model]["cost"] += call["cost"]
        return groups


class TokenBudgetManager:
    """Manages token budgets across multiple modules."""
    
    def __init__(self, budget_limit: float = 5.0):
        self.budget = TokenBudget(budget_limit=budget_limit)
        self.module_cache = {}  # Cache for already processed modules
    
    def prepare_module_for_llm(self, module_node: Any) -> str:
        """Prepare module code for LLM consumption."""
        # Extract relevant parts
        code_sections = []
        
        # Add module metadata
        code_sections.append(f"File: {module_node.path}")
        code_sections.append(f"Language: {module_node.language}")
        
        # Add imports (summarized)
        if module_node.imports:
            import_summary = f"Imports: {', '.join(module_node.imports[:10])}"
            if len(module_node.imports) > 10:
                import_summary += f" and {len(module_node.imports) - 10} more"
            code_sections.append(import_summary)
        
        # Add functions (summarized signatures)
        if module_node.public_functions:
            func_summary = f"Public functions: {', '.join(module_node.public_functions[:5])}"
            if len(module_node.public_functions) > 5:
                func_summary += f" and {len(module_node.public_functions) - 5} more"
            code_sections.append(func_summary)
        
        # Add classes
        if module_node.public_classes:
            code_sections.append(f"Classes: {', '.join(module_node.public_classes)}")
        
        # Add actual code (truncated if needed)
        code_sections.append("\n--- CODE ---")
        
        # Try to read actual file content
        try:
            with open(module_node.path, 'r', encoding='utf-8') as f:
                code = f.read()
                
                # Truncate if too long
                if self.budget.estimate_tokens(code) > 3000:
                    lines = code.split('\n')
                    # Take first 100 lines and last 50 lines
                    truncated = lines[:100] + ["..."] + lines[-50:]
                    code = '\n'.join(truncated)
                
                code_sections.append(code)
        except:
            code_sections.append("[Could not read file]")
        
        return '\n'.join(code_sections)
    
    def is_cached(self, module_path: str) -> bool:
        """Check if module is already processed."""
        return module_path in self.module_cache
    
    def get_cached(self, module_path: str):
        """Get cached result for module."""
        return self.module_cache.get(module_path)
    
    def cache_result(self, module_path: str, result: Any):
        """Cache result for module."""
        self.module_cache[module_path] = result