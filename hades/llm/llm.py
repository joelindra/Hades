import logging
import os
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any

import litellm
from jinja2 import (
    Environment,
    FileSystemLoader,
    select_autoescape,
)
from litellm import ModelResponse, completion_cost
from litellm.utils import supports_prompt_caching

from hades.llm.config import LLMConfig
from hades.llm.memory_compressor import MemoryCompressor
from hades.llm.request_queue import get_global_queue
from hades.llm.utils import _truncate_to_first_function, parse_tool_invocations
from hades.prompts import load_prompt_modules
from hades.tools import get_tools_prompt


import time
import uuid
import asyncio

logger = logging.getLogger(__name__)

# Global lazy loaders for local models
_TRANSFORMERS_MODEL = None
_TRANSFORMERS_PROCESSOR = None

def rotate_api_key(env_var_name: str):
    """Rotate to next API key when current one hits rate limit
    
    Args:
        env_var_name: Environment variable name (e.g., 'GOOGLE_API_KEY', 'OPENAI_API_KEY')
    
    Returns:
        bool: True if rotation was successful, False otherwise
    """
    try:
        script_dir = Path(__file__).parent.parent.parent
        env_file = script_dir / ".env"
        
        if not env_file.exists():
            return False
        
        # Read .env
        env_vars = {}
        with open(env_file, 'r', encoding='utf-8') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key.strip()] = value.strip()
        
        # Check if we have multiple API keys for this provider
        # Format: {ENV_VAR}_KEYS for multiple keys, {ENV_VAR}_INDEX for current index
        keys_var = f"{env_var_name}_KEYS"
        index_var = f"{env_var_name}_INDEX"
        
        if keys_var in env_vars:
            api_keys = env_vars[keys_var].split('\n')
            api_keys = [k.strip() for k in api_keys if k.strip()]
            
            if len(api_keys) <= 1:
                return False
            
            # Get current index
            current_index = int(env_vars.get(index_var, '0'))
            
            # Get current key before rotation (to check if this is active provider)
            current_key = env_vars.get(env_var_name, '')
            current_llm_key = env_vars.get('LLM_API_KEY', '')
            is_active_provider = (current_llm_key == current_key) if current_key else False
            
            # Rotate to next key (wrap around)
            next_index = (current_index + 1) % len(api_keys)
            
            # Update .env
            new_key = api_keys[next_index]
            env_vars[env_var_name] = new_key
            env_vars[index_var] = str(next_index)
            
            # Update litellm and environment
            litellm.api_key = new_key
            os.environ[env_var_name] = new_key
            
            # If this is the active provider, also update LLM_API_KEY
            if is_active_provider:
                env_vars['LLM_API_KEY'] = new_key
                os.environ['LLM_API_KEY'] = new_key
            
            # Write back
            with open(env_file, 'w', encoding='utf-8') as f:
                for key, value in env_vars.items():
                    f.write(f"{key}={value}\n")
            
            logger.info(f"Rotated {env_var_name} API key: {current_index + 1} -> {next_index + 1} (total: {len(api_keys)})")
            return True
        
        return False
    except Exception as e:
        logger.warning(f"Failed to rotate {env_var_name} API key: {e}")
        return False


def get_provider_env_var(model_name: str) -> str | None:
    """Get environment variable name for a given model
    
    Args:
        model_name: Model name (e.g., 'gemini/gemini-2.5-flash', 'openai/gpt-4')
    
    Returns:
        Environment variable name or None if not found
    """
    if not model_name:
        return None
    
    model_lower = model_name.lower()
    
    # Map model prefixes to env vars
    if 'gemini' in model_lower or 'google' in model_lower:
        return 'GOOGLE_API_KEY'
    elif 'gpt' in model_lower or 'openai' in model_lower:
        return 'OPENAI_API_KEY'
    elif 'claude' in model_lower or 'anthropic' in model_lower:
        return 'ANTHROPIC_API_KEY'
    elif 'mistral' in model_lower:
        return 'MISTRAL_API_KEY'
    elif 'groq' in model_lower:
        return 'GROQ_API_KEY'
    elif 'cohere' in model_lower:
        return 'COHERE_API_KEY'
    elif 'together' in model_lower:
        return 'TOGETHER_API_KEY'
    elif 'perplexity' in model_lower:
        return 'PERPLEXITY_API_KEY'
    elif 'deepinfra' in model_lower:
        return 'DEEPINFRA_API_KEY'
    elif 'anyscale' in model_lower:
        return 'ANYSCALE_API_KEY'
    elif 'replicate' in model_lower:
        return 'REPLICATE_API_KEY'
    elif 'fireworks' in model_lower:
        return 'FIREWORKS_API_KEY'
    elif 'huggingface' in model_lower:
        return 'HUGGINGFACE_API_KEY'
    elif 'openrouter' in model_lower:
        return 'OPENROUTER_API_KEY'
    elif 'azure' in model_lower:
        return 'AZURE_API_KEY'
    elif 'aws' in model_lower:
        return 'AWS_ACCESS_KEY_ID'
    elif 'ollama' in model_lower:
        return 'OLLAMA_API_KEY'
    elif 'deepseek' in model_lower:
        return 'DEEPSEEK_API_KEY'
    
    return None


api_key = os.getenv("LLM_API_KEY")
if api_key:
    litellm.api_key = api_key

api_base = (
    os.getenv("LLM_API_BASE")
    or os.getenv("OPENAI_API_BASE")
    or os.getenv("LITELLM_BASE_URL")
    or os.getenv("OLLAMA_API_BASE")
)
if api_base:
    litellm.api_base = api_base


class LLMRequestFailedError(Exception):
    def __init__(self, message: str, details: str | None = None):
        super().__init__(message)
        self.message = message
        self.details = details


MODELS_WITHOUT_STOP_WORDS = [
    "gpt-5",
    "gpt-5-mini",
    "gpt-5-nano",
    "o1-mini",
    "o1-preview",
    "o1",
    "o1-2024-12-17",
    "o3",
    "o3-2025-04-16",
    "o3-mini-2025-01-31",
    "o3-mini",
    "o4-mini",
    "o4-mini-2025-04-16",
    "grok-4-0709",
]

REASONING_EFFORT_SUPPORTED_MODELS = [
    "gpt-5",
    "gpt-5-mini",
    "gpt-5-nano",
    "o1-2024-12-17",
    "o1",
    "o3",
    "o3-2025-04-16",
    "o3-mini-2025-01-31",
    "o3-mini",
    "o4-mini",
    "o4-mini-2025-04-16",
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "step-3.5-flash",
]


class StepRole(str, Enum):
    AGENT = "agent"
    USER = "user"
    SYSTEM = "system"


@dataclass
class LLMResponse:
    content: str
    tool_invocations: list[dict[str, Any]] | None = None
    reasoning_details: str | None = None
    scan_id: str | None = None
    step_number: int = 1
    role: StepRole = StepRole.AGENT


@dataclass
class RequestStats:
    input_tokens: int = 0
    output_tokens: int = 0
    cached_tokens: int = 0
    cache_creation_tokens: int = 0
    cost: float = 0.0
    requests: int = 0
    failed_requests: int = 0

    def to_dict(self) -> dict[str, int | float]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cached_tokens": self.cached_tokens,
            "cache_creation_tokens": self.cache_creation_tokens,
            "cost": round(self.cost, 4),
            "requests": self.requests,
            "failed_requests": self.failed_requests,
        }


class LLM:
    def __init__(self, config: LLMConfig, agent_name: str | None = None):
        self.config = config
        self.agent_name = agent_name
        self._total_stats = RequestStats()
        self._last_request_stats = RequestStats()

        self.memory_compressor = MemoryCompressor()

        if agent_name:
            prompt_dir = Path(__file__).parent.parent / "agents" / agent_name
            prompts_dir = Path(__file__).parent.parent / "prompts"

            loader = FileSystemLoader([prompt_dir, prompts_dir])
            self.jinja_env = Environment(
                loader=loader,
                autoescape=select_autoescape(enabled_extensions=(), default_for_string=False),
            )

            try:
                prompt_module_content = load_prompt_modules(
                    self.config.prompt_modules or [], self.jinja_env
                )

                def get_module(name: str) -> str:
                    return prompt_module_content.get(name, "")

                self.jinja_env.globals["get_module"] = get_module

                self.system_prompt = self.jinja_env.get_template("system_prompt.jinja").render(
                    get_tools_prompt=get_tools_prompt,
                    loaded_module_names=list(prompt_module_content.keys()),
                    **prompt_module_content,
                )
            except (FileNotFoundError, OSError, ValueError) as e:
                logger.warning(f"Failed to load system prompt for {agent_name}: {e}")
                self.system_prompt = "You are a helpful AI assistant."
        else:
            self.system_prompt = "You are a helpful AI assistant."

    def _add_cache_control_to_content(
        self, content: str | list[dict[str, Any]]
    ) -> str | list[dict[str, Any]]:
        if isinstance(content, str):
            return [{"type": "text", "text": content, "cache_control": {"type": "ephemeral"}}]
        if isinstance(content, list) and content:
            last_item = content[-1]
            if isinstance(last_item, dict) and last_item.get("type") == "text":
                return content[:-1] + [{**last_item, "cache_control": {"type": "ephemeral"}}]
        return content

    def _is_anthropic_model(self) -> bool:
        if not self.config.model_name:
            return False
        model_lower = self.config.model_name.lower()
        return any(provider in model_lower for provider in ["anthropic/", "claude"])

    def _calculate_cache_interval(self, total_messages: int) -> int:
        if total_messages <= 1:
            return 10

        max_cached_messages = 3
        non_system_messages = total_messages - 1

        interval = 10
        while non_system_messages // interval > max_cached_messages:
            interval += 10

        return interval

    def _prepare_cached_messages(self, messages: list[dict[str, Any]]) -> list[dict[str, Any]]:
        if (
            not self.config.enable_prompt_caching
            or not supports_prompt_caching(self.config.model_name)
            or not messages
        ):
            return messages

        if not self._is_anthropic_model():
            return messages

        cached_messages = list(messages)

        if cached_messages and cached_messages[0].get("role") == "system":
            system_message = cached_messages[0].copy()
            system_message["content"] = self._add_cache_control_to_content(
                system_message["content"]
            )
            cached_messages[0] = system_message

        total_messages = len(cached_messages)
        if total_messages > 1:
            interval = self._calculate_cache_interval(total_messages)

            cached_count = 0
            for i in range(interval, total_messages, interval):
                if cached_count >= 3:
                    break

                if i < len(cached_messages):
                    message = cached_messages[i].copy()
                    message["content"] = self._add_cache_control_to_content(message["content"])
                    cached_messages[i] = message
                    cached_count += 1

        return cached_messages

    async def generate(  # noqa: PLR0912, PLR0915
        self,
        conversation_history: list[dict[str, Any]],
        scan_id: str | None = None,
        step_number: int = 1,
    ) -> LLMResponse:
        messages = [{"role": "system", "content": self.system_prompt}]

        # Compress history more aggressively for models with low TPM limits (Groq, Gemini free tier)
        model_name_lower = (self.config.model_name or "").lower()
        is_rate_limited_model = any(p in model_name_lower for p in ["groq", "gemini", "google"])
        
        if is_rate_limited_model:
            # More aggressive compression for models with low TPM limits
            # Keep only last 5 messages for Groq specifically as its limits are very tight
            max_msgs = 5 if "groq" in model_name_lower else 8
            compressed_history = list(self.memory_compressor.compress_history(conversation_history, max_messages=max_msgs))
        else:
            compressed_history = list(self.memory_compressor.compress_history(conversation_history))

        conversation_history.clear()
        conversation_history.extend(compressed_history)
        messages.extend(compressed_history)

        cached_messages = self._prepare_cached_messages(messages)

        try:
            response = await self._make_request(cached_messages)
            self._update_usage_stats(response)

            content = ""
            if (
                response.choices
                and hasattr(response.choices[0], "message")
                and response.choices[0].message
            ):
                content = getattr(response.choices[0].message, "content", "") or ""

            content = _truncate_to_first_function(content)

            if "</function>" in content:
                function_end_index = content.find("</function>") + len("</function>")
                content = content[:function_end_index]

            tool_invocations = parse_tool_invocations(content)

            # Extract reasoning_details for OpenRouter Aurora Alpha
            reasoning_details = None
            if (
                response.choices
                and hasattr(response.choices[0], "message")
                and hasattr(response.choices[0].message, "reasoning_details")
            ):
                reasoning_details = getattr(response.choices[0].message, "reasoning_details", None)

            return LLMResponse(
                scan_id=scan_id,
                step_number=step_number,
                role=StepRole.AGENT,
                content=content,
                tool_invocations=tool_invocations if tool_invocations else None,
                reasoning_details=reasoning_details,
            )

        except litellm.RateLimitError as e:
            error_str = str(e).lower()
            
            # Try to rotate API key for any provider if rate limited
            env_var = get_provider_env_var(self.config.model_name or "")
            if env_var:
                rotated = rotate_api_key(env_var)
                if rotated:
                    logger.info(f"Rotated {env_var} API key due to rate limit, waiting 5s then retrying request...")
                    await asyncio.sleep(5)  # Small cooldown after rotation
                    # Retry once with new key
                    try:
                        response = await self._make_request(cached_messages)
                        self._update_usage_stats(response)
                        
                        content = ""
                        if (
                            response.choices
                            and hasattr(response.choices[0], "message")
                            and response.choices[0].message
                        ):
                            content = getattr(response.choices[0].message, "content", "") or ""
                        
                        content = _truncate_to_first_function(content)
                        
                        if "</function>" in content:
                            function_end_index = content.find("</function>") + len("</function>")
                            content = content[:function_end_index]
                        
                        tool_invocations = parse_tool_invocations(content)
                        
                        return LLMResponse(
                            scan_id=scan_id,
                            step_number=step_number,
                            role=StepRole.AGENT,
                            content=content,
                            tool_invocations=tool_invocations if tool_invocations else None,
                        )
                    except Exception as retry_error:
                        logger.warning(f"Retry after API key rotation failed: {retry_error}")
                        # Fall through to raise original error
            
            if "tokens per minute" in error_str or "tpm" in error_str or "request too large" in error_str:
                raise LLMRequestFailedError(
                    "LLM request failed: Request too large for rate limit. Try reducing conversation history or using a model with higher limits.",
                    str(e)
                ) from e
            
            # If we reached here, rotation didn't happen or failed, and it's a general rate limit
            # Wait a bit and try one last time as a last resort
            logger.warning("No more keys to rotate or rotation failed. Waiting 30s before final retry...")
            await asyncio.sleep(30)
            try:
                response = await self._make_request(cached_messages)
                self._update_usage_stats(response)
                # ... process response same as above (omitted for brevity in replacement, but I should include it)
                content = ""
                if (
                    response.choices
                    and hasattr(response.choices[0], "message")
                    and response.choices[0].message
                ):
                    content = getattr(response.choices[0].message, "content", "") or ""
                
                content = _truncate_to_first_function(content)
                if "</function>" in content:
                    content = content[:content.find("</function>") + len("</function>")]
                
                tool_invocations = parse_tool_invocations(content)
                return LLMResponse(
                    scan_id=scan_id,
                    step_number=step_number,
                    role=StepRole.AGENT,
                    content=content,
                    tool_invocations=tool_invocations if tool_invocations else None,
                )
            except Exception as final_e:
                logger.error(f"Final retry after rate limit failed: {final_e}")
            
            raise LLMRequestFailedError(
                "LLM request failed: Rate limit exceeded. Try adding more API keys in .env or wait for your quota to reset.",
                str(e)
            ) from e
        except litellm.AuthenticationError as e:
            raise LLMRequestFailedError("LLM request failed: Invalid API key", str(e)) from e
        except litellm.NotFoundError as e:
            raise LLMRequestFailedError("LLM request failed: Model not found", str(e)) from e
        except litellm.ContextWindowExceededError as e:
            raise LLMRequestFailedError("LLM request failed: Context too long", str(e)) from e
        except litellm.ContentPolicyViolationError as e:
            raise LLMRequestFailedError(
                "LLM request failed: Content policy violation", str(e)
            ) from e
        except litellm.ServiceUnavailableError as e:
            raise LLMRequestFailedError("LLM request failed: Service unavailable", str(e)) from e
        except litellm.Timeout as e:
            raise LLMRequestFailedError("LLM request failed: Request timed out", str(e)) from e
        except litellm.UnprocessableEntityError as e:
            raise LLMRequestFailedError("LLM request failed: Unprocessable entity", str(e)) from e
        except litellm.InternalServerError as e:
            raise LLMRequestFailedError("LLM request failed: Internal server error", str(e)) from e
        except litellm.APIConnectionError as e:
            raise LLMRequestFailedError("LLM request failed: Connection error", str(e)) from e
        except litellm.UnsupportedParamsError as e:
            raise LLMRequestFailedError("LLM request failed: Unsupported parameters", str(e)) from e
        except litellm.BudgetExceededError as e:
            raise LLMRequestFailedError("LLM request failed: Budget exceeded", str(e)) from e
        except litellm.APIResponseValidationError as e:
            raise LLMRequestFailedError(
                "LLM request failed: Response validation error", str(e)
            ) from e
        except litellm.JSONSchemaValidationError as e:
            raise LLMRequestFailedError(
                "LLM request failed: JSON schema validation error", str(e)
            ) from e
        except litellm.InvalidRequestError as e:
            raise LLMRequestFailedError("LLM request failed: Invalid request", str(e)) from e
        except litellm.BadRequestError as e:
            raise LLMRequestFailedError("LLM request failed: Bad request", str(e)) from e
        except litellm.APIError as e:
            raise LLMRequestFailedError("LLM request failed: API error", str(e)) from e
        except litellm.OpenAIError as e:
            raise LLMRequestFailedError("LLM request failed: OpenAI error", str(e)) from e
        except Exception as e:
            raise LLMRequestFailedError(f"LLM request failed: {type(e).__name__}", str(e)) from e

    @property
    def usage_stats(self) -> dict[str, dict[str, int | float]]:
        return {
            "total": self._total_stats.to_dict(),
            "last_request": self._last_request_stats.to_dict(),
        }

    def get_cache_config(self) -> dict[str, bool]:
        return {
            "enabled": self.config.enable_prompt_caching,
            "supported": supports_prompt_caching(self.config.model_name),
        }

    def _should_include_stop_param(self) -> bool:
        if not self.config.model_name:
            return True

        actual_model_name = self.config.model_name.split("/")[-1].lower()
        model_name_lower = self.config.model_name.lower()

        return not any(
            actual_model_name == unsupported_model.lower()
            or model_name_lower == unsupported_model.lower()
            for unsupported_model in MODELS_WITHOUT_STOP_WORDS
        )

    def _should_include_reasoning_effort(self) -> bool:
        if not self.config.model_name:
            return False

        actual_model_name = self.config.model_name.split("/")[-1].lower()
        model_name_lower = self.config.model_name.lower()

        return any(
            actual_model_name == supported_model.lower()
            or model_name_lower == supported_model.lower()
            for supported_model in REASONING_EFFORT_SUPPORTED_MODELS
        )

    async def _make_request(
        self,
        messages: list[dict[str, Any]],
    ) -> ModelResponse:
        model_name = self.config.model_name or ""
        
        # New: Local Transformers Support
        if model_name.startswith("huggingface/"):
            return await self._make_local_transformers_request(messages, model_name)
        
        completion_args: dict[str, Any] = {
            "model": model_name,
            "messages": messages,
            "temperature": self.config.temperature,
            "timeout": 180,
        }

        # Handle custom api_base dynamically for custom/private models (e.g. SumoPod, Ollama)
        if api_base and not model_name.startswith("openrouter/") and not model_name.startswith("deepseek/"):
            completion_args["api_base"] = api_base
            completion_args["custom_llm_provider"] = "openai"
            # Strip the provider prefix (e.g. 'mimo/' or 'openai/') so the custom endpoint receives the raw model name
            if "/" in model_name:
                completion_args["model"] = model_name.split("/", 1)[1]

        # Explicitly handle OpenRouter models
        # OpenRouter expects the full model ID like "openrouter/z-ai/glm-5"
        # We set custom_llm_provider to tell LiteLLM to use OpenRouter
        # and keep the full model ID intact
        if model_name.startswith("openrouter/"):
            completion_args["custom_llm_provider"] = "openrouter"
            # Limit max_tokens for OpenRouter to prevent "insufficient credits" errors
            # Default is often 65536 which exceeds most free tier limits
            completion_args["max_tokens"] = 8000
            # Keep the full model ID as-is for OpenRouter
            # LiteLLM will pass this directly to OpenRouter's API
            
        # Handle DeepSeek explicitly using OpenAI-compatible protocol for maximum reliability
        if model_name.startswith("deepseek/"):
            completion_args["custom_llm_provider"] = "openai"
            completion_args["api_base"] = "https://api.deepseek.com"
            completion_args["model"] = model_name.replace("deepseek/", "deepseek-", 1) if "deepseek-" not in model_name else model_name.split("/")[-1]
            # Ensure model name is correct for DeepSeek's API (e.g., deepseek-chat)
            if "deepseek-chat" in model_name: completion_args["model"] = "deepseek-chat"
            if "deepseek-reasoner" in model_name: completion_args["model"] = "deepseek-reasoner"
            
            completion_args["api_key"] = os.getenv("DEEPSEEK_API_KEY") or os.getenv("LLM_API_KEY")

        # OpenRouter reasoning support (Step-3.5-Flash and Nemotron)
        if any(m in model_name.lower() for m in ["step-3.5-flash", "stepfun", "nemotron", "nvidia"]):
            completion_args["extra_body"] = {"reasoning": {"enabled": True}}

        if self._should_include_stop_param():
            completion_args["stop"] = ["</function>"]

        if self._should_include_reasoning_effort():
            completion_args["reasoning_effort"] = "high"

        queue = get_global_queue()
        response = await queue.make_request(completion_args)

        self._total_stats.requests += 1
        self._last_request_stats = RequestStats(requests=1)

        return response

    def _update_usage_stats(self, response: ModelResponse) -> None:
        try:
            if hasattr(response, "usage") and response.usage:
                input_tokens = getattr(response.usage, "prompt_tokens", 0)
                output_tokens = getattr(response.usage, "completion_tokens", 0)

                cached_tokens = 0
                cache_creation_tokens = 0

                if hasattr(response.usage, "prompt_tokens_details"):
                    prompt_details = response.usage.prompt_tokens_details
                    if hasattr(prompt_details, "cached_tokens"):
                        cached_tokens = prompt_details.cached_tokens or 0

                if hasattr(response.usage, "cache_creation_input_tokens"):
                    cache_creation_tokens = response.usage.cache_creation_input_tokens or 0

            else:
                input_tokens = 0
                output_tokens = 0
                cached_tokens = 0
                cache_creation_tokens = 0

            try:
                cost = completion_cost(response) or 0.0
            except Exception as e:  # noqa: BLE001
                logger.warning(f"Failed to calculate cost: {e}")
                cost = 0.0

            self._total_stats.input_tokens += input_tokens
            self._total_stats.output_tokens += output_tokens
            self._total_stats.cached_tokens += cached_tokens
            self._total_stats.cache_creation_tokens += cache_creation_tokens
            self._total_stats.cost += cost

            self._last_request_stats.input_tokens = input_tokens
            self._last_request_stats.output_tokens = output_tokens
            self._last_request_stats.cached_tokens = cached_tokens
            self._last_request_stats.cache_creation_tokens = cache_creation_tokens
            self._last_request_stats.cost = cost

            if cached_tokens > 0:
                logger.debug(f"Cache hit: {cached_tokens} cached tokens, {input_tokens} new tokens")
            if cache_creation_tokens > 0:
                logger.debug(f"Cache creation: {cache_creation_tokens} tokens written to cache")

            logger.debug(f"Usage stats: {self.usage_stats}")
        except Exception as e:  # noqa: BLE001
            logger.warning(f"Failed to update usage stats: {e}")

    async def _make_local_transformers_request(self, messages: list[dict[str, Any]], model_id: str) -> ModelResponse:
        """Handle execution of local models via Hugging Face Transformers"""
        global _TRANSFORMERS_MODEL, _TRANSFORMERS_PROCESSOR
        try:
            from transformers import AutoProcessor, AutoModelForImageTextToText
            import torch
            
            actual_model_id = model_id.replace("huggingface/", "", 1)
            
            if _TRANSFORMERS_MODEL is None:
                logger.info(f"Loading local model: {actual_model_id} (this may take a few minutes)...")
                _TRANSFORMERS_PROCESSOR = AutoProcessor.from_pretrained(
                    actual_model_id,
                    padding_side="left"
                )
                # Use bfloat16 for efficiency on Gemma/NVIDIA GPUs if available
                device = "cuda" if torch.cuda.is_available() else "cpu"
                _TRANSFORMERS_MODEL = AutoModelForImageTextToText.from_pretrained(
                    actual_model_id, 
                    device_map="auto" if device == "cuda" else None,
                    torch_dtype=torch.bfloat16 if device == "cuda" else torch.float32,
                    attn_implementation="sdpa" if device == "cuda" else None
                )
                logger.info(f"Model {actual_model_id} loaded successfully on {device}")

            # Process using the official chat template for correct tokenization/formatting
            try:
                inputs = _TRANSFORMERS_PROCESSOR.apply_chat_template(
                    messages,
                    tokenize=True,
                    add_generation_prompt=True,
                    return_dict=True,
                    return_tensors="pt"
                ).to(_TRANSFORMERS_MODEL.device)
            except Exception as e:
                logger.warning(f"Failed to apply chat template: {e}. Falling back to manual formatting.")
                full_prompt = "".join([f"{m.get('role', 'user')}: {m.get('content', '')}\n" for m in messages])
                full_prompt += "assistant: "
                inputs = _TRANSFORMERS_PROCESSOR(text=full_prompt, return_tensors="pt").to(_TRANSFORMERS_MODEL.device)

            input_len = inputs["input_ids"].shape[-1]
            
            with torch.no_grad():
                outputs = _TRANSFORMERS_MODEL.generate(
                    **inputs, 
                    max_new_tokens=1024,
                    temperature=0.7,
                    do_sample=True,
                    cache_implementation="static" if torch.cuda.is_available() else None
                )
            
            # Decode only the generated tokens
            generated_tokens = outputs[0][input_len:]
            response_text = _TRANSFORMERS_PROCESSOR.decode(generated_tokens, skip_special_tokens=True)
            
            # Wrap as litellm.ModelResponse
            resp = ModelResponse()
            resp.id = f"local-{uuid.uuid4()}"
            resp.model = model_id
            resp.object = "chat.completion"
            resp.created = int(time.time())
            
            from litellm.utils import Message, Choices
            msg_obj = Message(content=response_text, role="assistant")
            choice_obj = Choices(message=msg_obj, index=0, finish_reason="stop")
            resp.choices = [choice_obj]
            resp.usage = {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0}
            
            return resp
            
        except ImportError:
            raise LLMRequestFailedError(
                "Local model execution requires 'transformers' and 'torch'.",
                "Please run: pip install transformers torch torchvision accelerate"
            )
        except Exception as e:
            logger.error(f"Error in local model execution: {str(e)}")
            raise LLMRequestFailedError(f"Local LLM execution failed: {str(e)}")

