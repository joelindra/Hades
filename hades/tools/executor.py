import inspect
import logging
import os
import asyncio
from typing import Any

import httpx

logger = logging.getLogger(__name__)


if os.getenv("HADES_SANDBOX_MODE", "false").lower() == "false":
    from hades.runtime import get_runtime

from .argument_parser import convert_arguments
from .registry import (
    get_tool_by_name,
    get_tool_names,
    needs_agent_state,
    should_execute_in_sandbox,
)


async def execute_tool(tool_name: str, agent_state: Any | None = None, **kwargs: Any) -> Any:
    execute_in_sandbox = should_execute_in_sandbox(tool_name)
    sandbox_mode = os.getenv("HADES_SANDBOX_MODE", "false").lower() == "true"

    if execute_in_sandbox and not sandbox_mode:
        return await _execute_tool_in_sandbox(tool_name, agent_state, **kwargs)

    return await _execute_tool_locally(tool_name, agent_state, **kwargs)


async def _execute_tool_in_sandbox(tool_name: str, agent_state: Any, **kwargs: Any) -> Any:
    if not hasattr(agent_state, "sandbox_id") or not agent_state.sandbox_id:
        raise ValueError("Agent state with a valid sandbox_id is required for sandbox execution.")

    if not hasattr(agent_state, "sandbox_token") or not agent_state.sandbox_token:
        raise ValueError(
            "Agent state with a valid sandbox_token is required for sandbox execution."
        )

    if (
        not hasattr(agent_state, "sandbox_info")
        or "tool_server_port" not in agent_state.sandbox_info
    ):
        raise ValueError(
            "Agent state with a valid sandbox_info containing tool_server_port is required."
        )

    runtime = get_runtime()
    tool_server_port = agent_state.sandbox_info["tool_server_port"]
    server_url = await runtime.get_sandbox_url(agent_state.sandbox_id, tool_server_port)
    request_url = f"{server_url}/execute"

    agent_id = getattr(agent_state, "agent_id", "unknown")

    request_data = {
        "agent_id": agent_id,
        "tool_name": tool_name,
        "kwargs": kwargs,
    }

    headers = {
        "Authorization": f"Bearer {agent_state.sandbox_token}",
        "Content-Type": "application/json",
    }

    # Retry mechanism for tool server connection
    max_retries = 3
    retry_delay = 2
    
    for attempt in range(max_retries):
        async with httpx.AsyncClient(trust_env=False, timeout=httpx.Timeout(60.0)) as client:
            # First, try to check tool server health with retry
            health_url = f"{server_url}/health"
            health_ok = False
            
            for health_attempt in range(3):
                try:
                    health_response = await client.get(health_url, timeout=5.0)
                    if health_response.status_code == 200:
                        health_ok = True
                        break
                    else:
                        if health_attempt < 2:
                            await asyncio.sleep(1)
                            continue
                except httpx.RequestError:
                    if health_attempt < 2:
                        await asyncio.sleep(1)
                        continue
                    break
            
            if not health_ok:
                if attempt < max_retries - 1:
                    # Wait and retry
                    await asyncio.sleep(retry_delay * (attempt + 1))
                    continue
                else:
                    raise RuntimeError(
                        f"Cannot connect to tool server at {server_url} after {max_retries} attempts.\n"
                        f"This usually means:\n"
                        f"1. Docker container is not running or not ready\n"
                        f"2. Tool server failed to start inside container\n"
                        f"3. Port mapping issue (port {tool_server_port} not accessible)\n"
                        f"4. Network connectivity problem\n\n"
                        f"Try: Check Docker container status and logs"
                    )
            
            # Now try to execute the tool
            try:
                response = await client.post(
                    request_url, json=request_data, headers=headers, timeout=60.0
                )
                response.raise_for_status()
                response_data = response.json()
                if response_data.get("error"):
                    error_msg = response_data['error']
                    # If it's a temporary error, retry
                    if attempt < max_retries - 1 and (
                        "temporary" in error_msg.lower() or 
                        "timeout" in error_msg.lower() or
                        "connection" in error_msg.lower()
                    ):
                        await asyncio.sleep(retry_delay * (attempt + 1))
                        continue
                    raise RuntimeError(f"Sandbox execution error: {error_msg}")
                return response_data.get("result")
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 401:
                    raise RuntimeError(
                        "Authentication failed: Invalid or missing sandbox token. "
                        "Tool server may have been restarted or token expired."
                    ) from e
                elif e.response.status_code == 404:
                    raise RuntimeError(
                        f"Tool server endpoint not found. "
                        f"Server may be running but endpoint /execute is missing. "
                        f"URL: {request_url}"
                    ) from e
                elif e.response.status_code >= 500:
                    if attempt < max_retries - 1:
                        logger.warning(f"Tool server internal error (status {e.response.status_code}), retrying...")
                        await asyncio.sleep(retry_delay * (attempt + 1))
                        continue
                    raise RuntimeError(
                        f"Tool server internal error (status {e.response.status_code}). "
                        f"Server may be experiencing issues. Check container logs."
                    ) from e
                if attempt < max_retries - 1:
                    logger.warning(f"HTTP error {e.response.status_code}, retrying...")
                    await asyncio.sleep(retry_delay * (attempt + 1))
                    continue
                raise RuntimeError(
                    f"HTTP error calling tool server (status {e.response.status_code}): "
                    f"{e.response.text if hasattr(e.response, 'text') else 'No response body'}"
                ) from e
            except httpx.TimeoutException as e:
                if attempt < max_retries - 1:
                    logger.warning(f"Tool server timeout (attempt {attempt + 1}/{max_retries}), retrying...")
                    await asyncio.sleep(retry_delay * (attempt + 1))
                    continue
                raise RuntimeError(
                    f"Tool server request timed out after 60 seconds (attempt {attempt + 1}/{max_retries}). "
                    f"Server may be overloaded or tool execution is taking too long. "
                    f"URL: {request_url}"
                ) from e
            except httpx.RequestError as e:
                error_msg = str(e)
                if attempt < max_retries - 1:
                    # Retry on connection errors
                    if "Connection refused" in error_msg or "Name or service not known" in error_msg:
                        logger.warning(f"Tool server connection error (attempt {attempt + 1}/{max_retries}): {error_msg}")
                        await asyncio.sleep(retry_delay * (attempt + 1))
                        continue
                
                # Final attempt failed
                if "Connection refused" in error_msg or "Name or service not known" in error_msg:
                    raise RuntimeError(
                        f"Cannot connect to tool server at {server_url} after {max_retries} attempts.\n\n"
                        f"Possible causes:\n"
                        f"1. Docker container is not running\n"
                        f"2. Tool server failed to start inside container\n"
                        f"3. Port {tool_server_port} is not accessible from host\n"
                        f"4. Container networking issue\n\n"
                        f"Solutions:\n"
                        f"1. Check Docker: docker ps (should see hades-scan-* container)\n"
                        f"2. Check container logs: docker logs <container_id>\n"
                        f"3. Verify port mapping: docker port <container_id>\n"
                        f"4. Restart HADES to recreate container\n"
                        f"5. Check Docker daemon is running: docker info"
                    ) from e
                raise RuntimeError(
                    f"Request error calling tool server after {max_retries} attempts: {error_msg}\n"
                    f"URL: {request_url}\n"
                    f"Check Docker container status and network connectivity"
                ) from e


async def _execute_tool_locally(tool_name: str, agent_state: Any | None, **kwargs: Any) -> Any:
    tool_func = get_tool_by_name(tool_name)
    if not tool_func:
        raise ValueError(f"Tool '{tool_name}' not found")

    converted_kwargs = convert_arguments(tool_func, kwargs)

    if needs_agent_state(tool_name):
        if agent_state is None:
            raise ValueError(f"Tool '{tool_name}' requires agent_state but none was provided.")
        result = tool_func(agent_state=agent_state, **converted_kwargs)
    else:
        result = tool_func(**converted_kwargs)

    return await result if inspect.isawaitable(result) else result


def validate_tool_availability(tool_name: str | None) -> tuple[bool, str]:
    if tool_name is None:
        return False, "Tool name is missing"

    if tool_name not in get_tool_names():
        return False, f"Tool '{tool_name}' is not available"

    return True, ""


async def execute_tool_with_validation(
    tool_name: str | None, agent_state: Any | None = None, **kwargs: Any
) -> Any:
    is_valid, error_msg = validate_tool_availability(tool_name)
    if not is_valid:
        return f"Error: {error_msg}"

    assert tool_name is not None

    try:
        result = await execute_tool(tool_name, agent_state, **kwargs)
    except Exception as e:  # noqa: BLE001
        error_str = str(e)
        if len(error_str) > 500:
            error_str = error_str[:500] + "... [truncated]"
        return f"Error executing {tool_name}: {error_str}"
    else:
        return result


async def execute_tool_invocation(tool_inv: dict[str, Any], agent_state: Any | None = None) -> Any:
    tool_name = tool_inv.get("toolName")
    tool_args = tool_inv.get("args", {})

    return await execute_tool_with_validation(tool_name, agent_state, **tool_args)


def _check_error_result(result: Any) -> tuple[bool, Any]:
    is_error = False
    error_payload: Any = None

    if (isinstance(result, dict) and "error" in result) or (
        isinstance(result, str) and result.strip().lower().startswith("error:")
    ):
        is_error = True
        error_payload = result

    return is_error, error_payload


def _update_tracer_with_result(
    tracer: Any, execution_id: Any, is_error: bool, result: Any, error_payload: Any
) -> None:
    if not tracer or not execution_id:
        return

    try:
        if is_error:
            tracer.update_tool_execution(execution_id, "error", error_payload)
        else:
            tracer.update_tool_execution(execution_id, "completed", result)
    except (ConnectionError, RuntimeError) as e:
        error_msg = str(e)
        if tracer and execution_id:
            tracer.update_tool_execution(execution_id, "error", error_msg)
        raise


def _format_tool_result(tool_name: str, result: Any) -> tuple[str, list[dict[str, Any]]]:
    images: list[dict[str, Any]] = []

    screenshot_data = extract_screenshot_from_result(result)
    if screenshot_data:
        images.append(
            {
                "type": "image_url",
                "image_url": {"url": f"data:image/png;base64,{screenshot_data}"},
            }
        )
        result_str = remove_screenshot_from_result(result)
    else:
        result_str = result

    if result_str is None:
        final_result_str = f"Tool {tool_name} executed successfully"
    else:
        final_result_str = str(result_str)
        if len(final_result_str) > 10000:
            start_part = final_result_str[:4000]
            end_part = final_result_str[-4000:]
            final_result_str = start_part + "\n\n... [middle content truncated] ...\n\n" + end_part

    observation_xml = (
        f"<tool_result>\n<tool_name>{tool_name}</tool_name>\n"
        f"<result>{final_result_str}</result>\n</tool_result>"
    )

    return observation_xml, images


async def _execute_single_tool(
    tool_inv: dict[str, Any],
    agent_state: Any | None,
    tracer: Any | None,
    agent_id: str,
) -> tuple[str, list[dict[str, Any]], bool]:
    tool_name = tool_inv.get("toolName", "unknown")
    args = tool_inv.get("args", {})
    execution_id = None
    should_agent_finish = False

    if tracer:
        execution_id = tracer.log_tool_execution_start(agent_id, tool_name, args)

    try:
        result = await execute_tool_invocation(tool_inv, agent_state)

        is_error, error_payload = _check_error_result(result)

        if (
            tool_name in ("finish_scan", "agent_finish")
            and not is_error
            and isinstance(result, dict)
        ):
            if tool_name == "finish_scan":
                should_agent_finish = result.get("scan_completed", False)
            elif tool_name == "agent_finish":
                should_agent_finish = result.get("agent_completed", False)

        _update_tracer_with_result(tracer, execution_id, is_error, result, error_payload)

    except (ConnectionError, RuntimeError, ValueError, TypeError, OSError) as e:
        error_msg = str(e)
        if tracer and execution_id:
            tracer.update_tool_execution(execution_id, "error", error_msg)
        raise

    observation_xml, images = _format_tool_result(tool_name, result)
    return observation_xml, images, should_agent_finish


def _get_tracer_and_agent_id(agent_state: Any | None) -> tuple[Any | None, str]:
    try:
        from hades.telemetry.tracer import get_global_tracer

        tracer = get_global_tracer()
        agent_id = agent_state.agent_id if agent_state else "unknown_agent"
    except (ImportError, AttributeError):
        tracer = None
        agent_id = "unknown_agent"

    return tracer, agent_id


async def process_tool_invocations(
    tool_invocations: list[dict[str, Any]],
    conversation_history: list[dict[str, Any]],
    agent_state: Any | None = None,
) -> bool:
    observation_parts: list[str] = []
    all_images: list[dict[str, Any]] = []
    should_agent_finish = False

    tracer, agent_id = _get_tracer_and_agent_id(agent_state)

    for tool_inv in tool_invocations:
        observation_xml, images, tool_should_finish = await _execute_single_tool(
            tool_inv, agent_state, tracer, agent_id
        )
        observation_parts.append(observation_xml)
        all_images.extend(images)

        if tool_should_finish:
            should_agent_finish = True

    if all_images:
        content = [{"type": "text", "text": "Tool Results:\n\n" + "\n\n".join(observation_parts)}]
        content.extend(all_images)
        conversation_history.append({"role": "user", "content": content})
    else:
        observation_content = "Tool Results:\n\n" + "\n\n".join(observation_parts)
        conversation_history.append({"role": "user", "content": observation_content})

    return should_agent_finish


def extract_screenshot_from_result(result: Any) -> str | None:
    if not isinstance(result, dict):
        return None

    screenshot = result.get("screenshot")
    if isinstance(screenshot, str) and screenshot:
        return screenshot

    return None


def remove_screenshot_from_result(result: Any) -> Any:
    if not isinstance(result, dict):
        return result

    result_copy = result.copy()
    if "screenshot" in result_copy:
        result_copy["screenshot"] = "[Image data extracted - see attached image]"

    return result_copy
