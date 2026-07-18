import asyncio
import httpx
import contextlib
import logging
import os
import secrets
import socket
import time
from pathlib import Path
from typing import cast

import docker
from docker.errors import DockerException, ImageNotFound, NotFound
from docker.models.containers import Container

from .runtime import AbstractRuntime, SandboxInfo


HADES_IMAGE = os.getenv("HADES_IMAGE", "ghcr.io/joelindra/hades-sandbox-now:v1.0")
HADES_FALLBACK_IMAGE = "ghcr.io/joelindra/hades-sandbox-now:v1.0"
logger = logging.getLogger(__name__)


class DockerRuntime(AbstractRuntime):
    def __init__(self) -> None:
        try:
            # Increase timeout for large images (e.g. 16GB+)
            self.client = docker.from_env(timeout=300)
            # Perform a quick connection check
            self.client.ping()
        except DockerException as e:
            logger.error("Failed to connect to Docker daemon: %s", e)
            
            error_hint = ""
            if os.path.exists("/proc/version"):
                with open("/proc/version", "r") as f:
                    version_info = f.read()
                    if "Microsoft" in version_info or "WSL" in version_info:
                        error_hint = (
                            "\n[HADES HINT] WSL DETECTED!\n"
                            "1. Try starting Docker service: sudo service docker start\n"
                            "2. Ensure you are in 'docker' group: sudo usermod -aG docker $USER && newgrp docker\n"
                            "3. If using Docker Desktop, enable WSL integration for your distro in Settings."
                        )
                    else:
                        error_hint = (
                            "\n[HADES HINT] LINUX DETECTED!\n"
                            "1. Check if Docker is running: sudo systemctl start docker\n"
                            "2. Check permissions: sudo usermod -aG docker $USER && newgrp docker"
                        )
            
            raise RuntimeError(
                f"Docker is not available or not configured correctly.{error_hint}\n"
                f"Original error: {e}"
            ) from e

        self._scan_container: Container | None = None
        self._tool_server_port: int | None = None
        self._tool_server_token: str | None = None

    def _generate_sandbox_token(self) -> str:
        return secrets.token_urlsafe(32)

    def _find_available_port(self) -> int:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind(("", 0))
            return cast("int", s.getsockname()[1])

    def _get_scan_id(self, agent_id: str) -> str:
        try:
            from hades.telemetry.tracer import get_global_tracer

            tracer = get_global_tracer()
            if tracer and tracer.scan_config:
                return str(tracer.scan_config.get("scan_id", "default-scan"))
        except ImportError:
            logger.debug("Failed to import tracer, using fallback scan ID")
        except AttributeError:
            logger.debug("Tracer missing scan_config, using fallback scan ID")

        return f"scan-{agent_id.split('-')[0]}"

    async def _verify_image_available(self, image_name: str, max_retries: int = 3) -> None:
        def _validate_image(image: docker.models.images.Image) -> None:
            if not image.id or not image.attrs:
                raise ImageNotFound(f"Image {image_name} metadata incomplete")

        for attempt in range(max_retries):
            try:
                image = self.client.images.get(image_name)
                _validate_image(image)
            except ImageNotFound:
                if attempt == max_retries - 1:
                    logger.exception(f"Image {image_name} not found after {max_retries} attempts")
                    raise
                logger.warning(f"Image {image_name} not ready, attempt {attempt + 1}/{max_retries}")
                await asyncio.sleep(2**attempt)
            except DockerException:
                if attempt == max_retries - 1:
                    logger.exception(f"Failed to verify image {image_name}")
                    raise
                logger.warning(f"Docker error verifying image, attempt {attempt + 1}/{max_retries}")
                await asyncio.sleep(2**attempt)
            else:
                logger.debug(f"Image {image_name} verified as available")
                return

    async def _create_container_with_retry(self, scan_id: str, max_retries: int = 3) -> Container:
        last_exception = None
        container_name = f"hades-scan-{scan_id}"

        for attempt in range(max_retries):
            try:
                # Try primary image first
                current_image = HADES_IMAGE
                try:
                    await self._verify_image_available(current_image)
                except (DockerException, ImageNotFound):
                    logger.warning(f"Primary image {HADES_IMAGE} failed, trying fallback {HADES_FALLBACK_IMAGE}")
                    current_image = HADES_FALLBACK_IMAGE
                    await self._verify_image_available(current_image)

                try:
                    existing_container = self.client.containers.get(container_name)
                    logger.warning(f"Container {container_name} already exists, removing it")
                    with contextlib.suppress(Exception):
                        existing_container.stop(timeout=5)
                    existing_container.remove(force=True)
                    await asyncio.sleep(1)
                except NotFound:
                    pass
                except DockerException as e:
                    logger.warning(f"Error checking/removing existing container: {e}")

                caido_port = self._find_available_port()
                tool_server_port = self._find_available_port()
                tool_server_token = self._generate_sandbox_token()

                self._tool_server_port = tool_server_port
                self._tool_server_token = tool_server_token

                container = self.client.containers.run(
                    current_image,
                    command="sleep infinity",
                    detach=True,
                    name=container_name,
                    hostname=f"hades-scan-{scan_id}",
                    ports={
                        f"{caido_port}/tcp": caido_port,
                        f"{tool_server_port}/tcp": tool_server_port,
                    },
                    cap_add=["NET_ADMIN", "NET_RAW"],
                    labels={"hades-scan-id": scan_id},
                    environment={
                        "PYTHONUNBUFFERED": "1",
                        "CAIDO_PORT": str(caido_port),
                        "TOOL_SERVER_PORT": str(tool_server_port),
                        "TOOL_SERVER_TOKEN": tool_server_token,
                    },
                    tty=True,
                )

                self._scan_container = container
                logger.debug("Created container %s for scan %s", container.id, scan_id)

                await self._initialize_container(
                    container, caido_port, tool_server_port, tool_server_token
                )
            except DockerException as e:
                last_exception = e
                if attempt == max_retries - 1:
                    logger.exception(f"Failed to create container after {max_retries} attempts")
                    break

                logger.warning(f"Container creation attempt {attempt + 1}/{max_retries} failed")

                self._tool_server_port = None
                self._tool_server_token = None

                sleep_time = (2**attempt) + (0.1 * attempt)
                await asyncio.sleep(sleep_time)
            else:
                return container

        raise RuntimeError(
            f"Failed to create Docker container after {max_retries} attempts: {last_exception}"
        ) from last_exception

    async def _get_or_create_scan_container(self, scan_id: str) -> Container:  # noqa: PLR0912
        container_name = f"hades-scan-{scan_id}"

        if self._scan_container:
            try:
                self._scan_container.reload()
                if self._scan_container.status == "running":
                    return self._scan_container
            except NotFound:
                self._scan_container = None
                self._tool_server_port = None
                self._tool_server_token = None

        try:
            container = self.client.containers.get(container_name)
            container.reload()

            if (
                "hades-scan-id" not in container.labels
                or container.labels["hades-scan-id"] != scan_id
            ):
                logger.warning(
                    f"Container {container_name} exists but missing/wrong label, updating"
                )

            if container.status != "running":
                logger.debug(f"Starting existing container {container_name}")
                container.start()
                await asyncio.sleep(2)

            self._scan_container = container

            for env_var in container.attrs["Config"]["Env"]:
                if env_var.startswith("TOOL_SERVER_PORT="):
                    self._tool_server_port = int(env_var.split("=")[1])
                elif env_var.startswith("TOOL_SERVER_TOKEN="):
                    self._tool_server_token = env_var.split("=")[1]

            logger.info(f"Reusing existing container {container_name}")

        except NotFound:
            pass
        except DockerException as e:
            logger.warning(f"Failed to get container by name {container_name}: {e}")
        else:
            return container

        try:
            containers = self.client.containers.list(
                all=True, filters={"label": f"hades-scan-id={scan_id}"}
            )
            if containers:
                container = cast("Container", containers[0])
                if container.status != "running":
                    container.start()
                    await asyncio.sleep(2)
                self._scan_container = container

                for env_var in container.attrs["Config"]["Env"]:
                    if env_var.startswith("TOOL_SERVER_PORT="):
                        self._tool_server_port = int(env_var.split("=")[1])
                    elif env_var.startswith("TOOL_SERVER_TOKEN="):
                        self._tool_server_token = env_var.split("=")[1]

                logger.debug(f"Found existing container by label for scan {scan_id}")
                return container
        except DockerException as e:
            logger.warning("Failed to find existing container by label for scan %s: %s", scan_id, e)

        logger.info("Creating new Docker container for scan %s", scan_id)
        return await self._create_container_with_retry(scan_id)

    async def _initialize_container(
        self, container: Container, caido_port: int, tool_server_port: int, tool_server_token: str
    ) -> None:
        logger.debug("Initializing Caido proxy on port %s", caido_port)
        result = container.exec_run(
            f"bash -c 'export CAIDO_PORT={caido_port} && /usr/local/bin/docker-entrypoint.sh true'",
            detach=False,
        )

        # Increased wait for Caido and entrypoint to fully initialize
        logger.debug("Waiting 12 seconds for Caido services to stabilize...")
        await asyncio.sleep(12)

        result = container.exec_run(
            "bash -c 'source /etc/profile.d/proxy.sh && echo $CAIDO_API_TOKEN'", user="pentester"
        )
        caido_token = result.output.decode().strip() if result.exit_code == 0 else ""

        # Try to locate tool_server.py more flexibly
        logger.debug("Locating tool_server.py in container...")
        
        find_cmd = (
            "bash -c 'cd /app && "
            "if [ -f hades/runtime/tool_server.py ]; then echo \"hades:/app/hades/runtime/tool_server.py\"; "
            "elif [ -f strix/runtime/tool_server.py ]; then echo \"strix:/app/strix/runtime/tool_server.py\"; "
            "else "
            "  FOUND=$(find /app -name tool_server.py | head -n 1); "
            "  if [ -n \"$FOUND\" ]; then "
            "    if [[ \"$FOUND\" == *\"hades\"* ]]; then echo \"hades:$FOUND\"; else echo \"strix:$FOUND\"; fi; "
            "  else echo \"none:none\"; fi; "
            "fi'"
        )
        
        check_result = container.exec_run(find_cmd, user="pentester")
        result_str = check_result.output.decode().strip() if check_result.exit_code == 0 else "none:none"
        tool_server_type, tool_server_path = result_str.split(":", 1)
        
        if tool_server_type == "none":
            # Final attempt: search the whole container just in case
            logger.warning("tool_server.py not found in /app, searching system-wide...")
            check_result = container.exec_run("find / -name tool_server.py | head -n 1", user="pentester")
            tool_server_path = check_result.output.decode().strip()
            if not tool_server_path:
                logger.error("tool_server.py not found anywhere in the container")
                raise RuntimeError("tool_server.py not found in container. Please check your Docker image.")
            tool_server_type = "hades" if "hades" in tool_server_path else "strix"

        logger.debug("Found %s tool_server.py at: %s", tool_server_type, tool_server_path)
        
        # Start tool server in background
        logger.debug("Starting tool server in background...")
        
        # Verify container is still running before exec
        container.reload()
        if container.status != "running":
            logger.error("Container stopped unexpectedly (status: %s)", container.status)
            raise RuntimeError(f"Container died before initialization could complete (status: {container.status})")

        # Ensure we always run in sandbox mode
        env_mode = "HADES_SANDBOX_MODE=true"

        # Use absolute path for tool server and ensure it runs with unbuffered output
        exec_command = (
            f"bash -c 'source /etc/profile.d/proxy.sh 2>/dev/null || true && "
            f"export CAIDO_API_TOKEN=\"{caido_token}\" && "
            f"export CAIDO_PORT=\"{caido_port}\" && "
            f"export {env_mode} && "
            f"python3 -u \"{tool_server_path}\" "
            f"--token \"{tool_server_token}\" "
            f"--host 0.0.0.0 "
            f"--port \"{tool_server_port}\" "
            f"> /tmp/tool_server.log 2>&1 &'"
        )

        try:
            container.exec_run(
                exec_command,
                detach=True,
                user="pentester",
            )
        except Exception as e:
            logger.error("Failed to execute tool server: %s", str(e))
            # Try once more without the specific user if it failed (fallback to root/default)
            logger.debug("Retrying exec without specific user...")
            container.exec_run(exec_command, detach=True)

        # Wait for tool server to be ready (check from host using mapped port)
        logger.debug("Waiting for tool server to be ready on port %s", tool_server_port)
        
        max_retries = 20
        retry_delay = 1
        
        async def check_tool_server_health():
            # Check from host machine using the mapped port
            # The port mapping is {tool_server_port}/tcp: {tool_server_port}
            # So we use 127.0.0.1:{tool_server_port} from the host
            api_url = f"http://127.0.0.1:{tool_server_port}"
            for attempt in range(max_retries):
                try:
                    async with httpx.AsyncClient(timeout=5.0) as client:
                        response = await client.get(f"{api_url}/health")
                        if response.status_code == 200:
                            health_data = response.json()
                            logger.info(
                                "Tool server is ready after %d attempts. Health: %s",
                                attempt + 1,
                                health_data.get("status", "unknown")
                            )
                            return True
                        else:
                            logger.debug(
                                "Tool server health check returned status %d. Output: %s (attempt %d/%d)",
                                response.status_code,
                                response.text[:100],
                                attempt + 1,
                                max_retries
                            )
                except (httpx.ConnectError, httpx.RemoteProtocolError) as e:
                    if attempt < max_retries - 1:
                        logger.debug(
                            "Tool server not ready (connection error: %s). Attempt %d/%d, waiting...",
                            str(e),
                            attempt + 1,
                            max_retries
                        )
                        await asyncio.sleep(retry_delay)
                    else:
                        logger.warning(
                            "Tool server connection failed after %d attempts. "
                            "This may be normal if the server is still starting or crashing.",
                            max_retries
                        )
                except Exception as e:
                    if attempt < max_retries - 1:
                        logger.debug(
                            "Tool server health check error (attempt %d/%d): %s",
                            attempt + 1,
                            max_retries,
                            e
                        )
                        await asyncio.sleep(retry_delay)
                    else:
                        logger.warning(
                            "Tool server health check failed after %d attempts: %s",
                            max_retries,
                            e
                        )
                        # Check logs for debugging
                        try:
                            log_result = container.exec_run(
                                "cat /tmp/tool_server.log 2>/dev/null || echo 'No logs available'",
                                user="pentester"
                            )
                            log_output = (
                                log_result.output.decode()
                                if log_result.exit_code == 0
                                else "Could not read logs"
                            )
                            logger.debug("Tool server logs (last 500 chars): %s", log_output[-500:])
                        except Exception:
                            pass
            return False
        
        try:
            # Run health check from host
            health_result = await check_tool_server_health()
            if not health_result:
                logger.warning(
                    "Tool server health check did not succeed, but continuing. "
                    "Server may still be starting up."
                )
        except Exception as e:
            logger.warning("Error checking tool server health: %s. Continuing anyway.", e)

        # Additional wait to ensure server is fully ready
        await asyncio.sleep(3)

    def _copy_local_directory_to_container(
        self, container: Container, local_path: str, target_name: str | None = None
    ) -> None:
        import tarfile
        from io import BytesIO

        try:
            local_path_obj = Path(local_path).resolve()
            if not local_path_obj.exists() or not local_path_obj.is_dir():
                logger.warning(f"Local path does not exist or is not directory: {local_path_obj}")
                return

            if target_name:
                logger.info(
                    f"Copying local directory {local_path_obj} to container at "
                    f"/workspace/{target_name}"
                )
            else:
                logger.info(f"Copying local directory {local_path_obj} to container")

            tar_buffer = BytesIO()
            with tarfile.open(fileobj=tar_buffer, mode="w") as tar:
                for item in local_path_obj.rglob("*"):
                    if item.is_file():
                        rel_path = item.relative_to(local_path_obj)
                        arcname = Path(target_name) / rel_path if target_name else rel_path
                        tar.add(item, arcname=arcname)

            tar_buffer.seek(0)
            container.put_archive("/workspace", tar_buffer.getvalue())

            container.exec_run(
                "chown -R pentester:pentester /workspace && chmod -R 755 /workspace",
                user="root",
            )

            logger.debug("Successfully copied local directory to /workspace")

        except (OSError, DockerException):
            logger.exception("Failed to copy local directory to container")

    async def create_sandbox(
        self,
        agent_id: str,
        existing_token: str | None = None,
        local_sources: list[dict[str, str]] | None = None,
    ) -> SandboxInfo:
        scan_id = self._get_scan_id(agent_id)
        container = await self._get_or_create_scan_container(scan_id)

        source_copied_key = f"_source_copied_{scan_id}"
        if local_sources and not hasattr(self, source_copied_key):
            for index, source in enumerate(local_sources, start=1):
                source_path = source.get("source_path")
                if not source_path:
                    continue

                target_name = source.get("workspace_subdir")
                if not target_name:
                    target_name = Path(source_path).name or f"target_{index}"

                self._copy_local_directory_to_container(container, source_path, target_name)
            setattr(self, source_copied_key, True)

        container_id = container.id
        if container_id is None:
            raise RuntimeError("Docker container ID is unexpectedly None")

        token = existing_token if existing_token is not None else self._tool_server_token

        if self._tool_server_port is None or token is None:
            raise RuntimeError("Tool server not initialized or no token available")

        api_url = await self.get_sandbox_url(container_id, self._tool_server_port)

        await self._register_agent_with_tool_server(api_url, agent_id, token)

        return {
            "workspace_id": container_id,
            "api_url": api_url,
            "auth_token": token,
            "tool_server_port": self._tool_server_port,
            "agent_id": agent_id,
        }

    async def _register_agent_with_tool_server(
        self, api_url: str, agent_id: str, token: str
    ) -> None:
        try:
            async with httpx.AsyncClient(trust_env=False) as client:
                response = await client.post(
                    f"{api_url}/register_agent",
                    params={"agent_id": agent_id},
                    headers={"Authorization": f"Bearer {token}"},
                    timeout=30,
                )
                response.raise_for_status()
                logger.info(f"Registered agent {agent_id} with tool server")
        except (httpx.RequestError, httpx.HTTPStatusError) as e:
            logger.warning(f"Failed to register agent {agent_id}: {e}")

    async def get_sandbox_url(self, container_id: str, port: int) -> str:
        try:
            container = self.client.containers.get(container_id)
            container.reload()

            host = "127.0.0.1"
            if "DOCKER_HOST" in os.environ:
                docker_host = os.environ["DOCKER_HOST"]
                if "://" in docker_host:
                    host = docker_host.split("://")[1].split(":")[0]

        except NotFound:
            raise ValueError(f"Container {container_id} not found.") from None
        except DockerException as e:
            raise RuntimeError(f"Failed to get container URL for {container_id}: {e}") from e
        else:
            return f"http://{host}:{port}"

    async def destroy_sandbox(self, container_id: str) -> None:
        logger.info("Destroying scan container %s", container_id)
        try:
            container = self.client.containers.get(container_id)
            container.stop()
            container.remove()
            logger.info("Successfully destroyed container %s", container_id)

            self._scan_container = None
            self._tool_server_port = None
            self._tool_server_token = None

        except NotFound:
            logger.warning("Container %s not found for destruction.", container_id)
        except DockerException as e:
            logger.warning("Failed to destroy container %s: %s", container_id, e)
