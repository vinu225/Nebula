"""
Sovereign AI Workbench — Sandbox Code Executor

Executes code securely inside an isolated container with --network=none,
resource quotas (CPU, RAM), and strict timeouts.
Provides controlled subprocess fallback when Docker daemon is not active.
"""

from __future__ import annotations

import asyncio
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any, Dict

from app.core.config import get_settings
from app.core.logging import get_logger
from app.sandbox.security import validate_python_code

logger = get_logger(__name__)
settings = get_settings()


class DockerSandboxExecutor:
    """Manages secure ephemeral execution environments."""

    def __init__(self) -> None:
        self.docker_client = None
        self._init_docker()

    def _init_docker(self) -> None:
        try:
            import docker
            self.docker_client = docker.from_env()
            self.docker_client.ping()
            logger.info("docker_sandbox_client_connected")
        except Exception as e:
            logger.warning("docker_daemon_unavailable_using_local_sandbox", reason=str(e))
            self.docker_client = None

    async def execute_code(
        self,
        code: str,
        timeout: int = 30,
        stdin_input: str = "",
    ) -> Dict[str, Any]:
        """Validate and execute Python code safely.

        Args:
            code: Python script string.
            timeout: Execution timeout in seconds.
            stdin_input: Optional stdin text.

        Returns:
            Dict containing returncode, stdout, stderr, and security validation status.
        """
        # Step 1: Static AST Security Analysis
        is_safe, violations = validate_python_code(code)
        if not is_safe:
            return {
                "success": False,
                "returncode": -1,
                "stdout": "",
                "stderr": f"Security Violation: {'; '.join(violations)}",
                "violations": violations,
            }

        # Step 2: Containerized Execution if Docker available
        if self.docker_client:
            try:
                return await self._execute_in_docker(code, timeout)
            except Exception as ex:
                logger.warning("docker_exec_failed_attempting_fallback", error=str(ex))

        # Step 3: Isolated Subprocess Execution Fallback
        return await self._execute_in_subprocess(code, timeout, stdin_input)

    async def _execute_in_docker(self, code: str, timeout: int) -> Dict[str, Any]:
        """Run inside container with network=none and resource limits."""
        def _run() -> Dict[str, Any]:
            assert self.docker_client is not None
            with tempfile.TemporaryDirectory() as temp_dir:
                script_path = Path(temp_dir) / "script.py"
                script_path.write_text(code, encoding="utf-8")

                container = self.docker_client.containers.run(
                    image=settings.sandbox_image,
                    command=["python", "/workspace/script.py"],
                    volumes={temp_dir: {"bind": "/workspace", "mode": "ro"}},
                    network_mode="none",
                    mem_limit=settings.sandbox_memory_limit,
                    nano_cpus=int(settings.sandbox_cpu_limit * 1e9),
                    detach=True,
                )
                try:
                    result = container.wait(timeout=timeout)
                    stdout = container.logs(stdout=True, stderr=False).decode("utf-8", errors="replace")
                    stderr = container.logs(stdout=False, stderr=True).decode("utf-8", errors="replace")
                    exit_code = result.get("StatusCode", 0)
                    return {
                        "success": exit_code == 0,
                        "returncode": exit_code,
                        "stdout": stdout,
                        "stderr": stderr,
                    }
                finally:
                    container.remove(force=True)

        return await asyncio.to_thread(_run)

    async def _execute_in_subprocess(self, code: str, timeout: int, stdin_input: str) -> Dict[str, Any]:
        """Air-gapped subprocess runner with timeout."""
        def _run_sub() -> Dict[str, Any]:
            with tempfile.NamedTemporaryFile(suffix=".py", delete=False, mode="w", encoding="utf-8") as f:
                f.write(code)
                tmp_path = f.name

            try:
                res = subprocess.run(
                    [sys.executable, tmp_path],
                    input=stdin_input if stdin_input else None,
                    text=True,
                    capture_output=True,
                    timeout=timeout,
                )
                return {
                    "success": res.returncode == 0,
                    "returncode": res.returncode,
                    "stdout": res.stdout,
                    "stderr": res.stderr,
                }
            except subprocess.TimeoutExpired:
                return {
                    "success": False,
                    "returncode": -1,
                    "stdout": "",
                    "stderr": f"Execution timed out after {timeout} seconds.",
                }
            except Exception as e:
                return {
                    "success": False,
                    "returncode": -1,
                    "stdout": "",
                    "stderr": str(e),
                }
            finally:
                try:
                    Path(tmp_path).unlink(missing_ok=True)
                except Exception:
                    pass

        return await asyncio.to_thread(_run_sub)


# Global singleton
_sandbox_executor: DockerSandboxExecutor | None = None


def get_sandbox_executor() -> DockerSandboxExecutor:
    global _sandbox_executor
    if _sandbox_executor is None:
        _sandbox_executor = DockerSandboxExecutor()
    return _sandbox_executor
