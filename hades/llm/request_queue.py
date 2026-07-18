import asyncio
import logging
import threading
import time
from typing import Any

import litellm
from litellm import ModelResponse, completion
from tenacity import before_sleep_log, retry, retry_if_exception, stop_after_attempt, wait_exponential


logger = logging.getLogger(__name__)


def should_retry_exception(exception: Exception) -> bool:
    # Check for rate limit errors (including TPM/TPD limits)
    if isinstance(exception, litellm.RateLimitError):
        error_str = str(exception).lower()
        # Retry for rate limit errors, but with longer delays
        if "tokens per minute" in error_str or "tpm" in error_str:
            # Request too large - will need to reduce size, but retry once
            return True
        # General rate limit - retry with backoff
        return True
    
    status_code = None

    if hasattr(exception, "status_code"):
        status_code = exception.status_code
    elif hasattr(exception, "response") and hasattr(exception.response, "status_code"):
        status_code = exception.response.status_code

    if status_code is not None:
        return bool(litellm._should_retry(status_code))
    return True


class LLMRequestQueue:
    def __init__(self, max_concurrent: int = 6, delay_between_requests: float = 1.0):
        self.max_concurrent = max_concurrent
        self.delay_between_requests = delay_between_requests
        self._semaphore = threading.BoundedSemaphore(max_concurrent)
        self._last_request_time = 0.0
        self._lock = threading.Lock()

    async def make_request(self, completion_args: dict[str, Any]) -> ModelResponse:
        try:
            while not self._semaphore.acquire(timeout=0.2):
                await asyncio.sleep(0.1)

            with self._lock:
                now = time.time()
                time_since_last = now - self._last_request_time
                sleep_needed = max(0, self.delay_between_requests - time_since_last)
                self._last_request_time = now + sleep_needed

            if sleep_needed > 0:
                await asyncio.sleep(sleep_needed)

            return await self._reliable_request(completion_args)
        finally:
            self._semaphore.release()

    def _is_rate_limit_error(self, exception: Exception) -> bool:
        """Check if exception is a rate limit error"""
        if isinstance(exception, litellm.RateLimitError):
            return True
        error_str = str(exception).lower()
        return "rate limit" in error_str or "tokens per minute" in error_str or "tpm" in error_str

    @retry(  # type: ignore[misc]
        stop=stop_after_attempt(6),
        wait=wait_exponential(multiplier=5, min=10, max=120),
        retry=retry_if_exception(should_retry_exception),
        reraise=True,
        before_sleep=before_sleep_log(logger, logging.DEBUG)
    )
    async def _reliable_request(self, completion_args: dict[str, Any]) -> ModelResponse:
        try:
            # Ensure we're using the latest API key from environment
            import os
            # Try to get API key from LLM_API_KEY first, then check common provider env vars
            current_api_key = os.getenv("LLM_API_KEY")
            if not current_api_key:
                # Check common provider env vars
                for env_var in ["GOOGLE_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", 
                               "MISTRAL_API_KEY", "GROQ_API_KEY", "COHERE_API_KEY",
                               "TOGETHER_API_KEY", "PERPLEXITY_API_KEY", "DEEPINFRA_API_KEY"]:
                    current_api_key = os.getenv(env_var)
                    if current_api_key:
                        break
            if current_api_key and current_api_key != litellm.api_key:
                litellm.api_key = current_api_key
            
            response = completion(**completion_args, stream=False)
            if isinstance(response, ModelResponse):
                return response
            self._raise_unexpected_response()
            raise RuntimeError("Unreachable code")
        except litellm.RateLimitError as e:
            error_str = str(e).lower()
            # If request is too large (TPM limit), we need to reduce message size
            if "tokens per minute" in error_str or "tpm" in error_str or "request too large" in error_str:
                logger.warning(f"Rate limit due to large request: {e}")
                # Wait longer before retrying for large requests
                await asyncio.sleep(10)
            raise

    def _raise_unexpected_response(self) -> None:
        raise RuntimeError("Unexpected response type")


_global_queue: LLMRequestQueue | None = None


def get_global_queue() -> LLMRequestQueue:
    global _global_queue  # noqa: PLW0603
    if _global_queue is None:
        _global_queue = LLMRequestQueue()
    return _global_queue

