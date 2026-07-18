import logging
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional
from uuid import uuid4


if TYPE_CHECKING:
    from collections.abc import Callable


logger = logging.getLogger(__name__)

_global_tracer: Optional["Tracer"] = None


def get_global_tracer() -> Optional["Tracer"]:
    return _global_tracer


def set_global_tracer(tracer: "Tracer") -> None:
    global _global_tracer  # noqa: PLW0603
    _global_tracer = tracer


class Tracer:
    def __init__(self, run_name: str | None = None):
        self.run_name = run_name
        self.run_id = run_name or f"run-{uuid4().hex[:8]}"
        self.start_time = datetime.now(UTC).isoformat()
        self.end_time: str | None = None

        self.agents: dict[str, dict[str, Any]] = {}
        self.tool_executions: dict[int, dict[str, Any]] = {}
        self.chat_messages: list[dict[str, Any]] = []

        self.vulnerability_reports: list[dict[str, Any]] = []
        self.final_scan_result: str | None = None

        self.scan_results: dict[str, Any] | None = None
        self.scan_config: dict[str, Any] | None = None
        self.run_metadata: dict[str, Any] = {
            "run_id": self.run_id,
            "run_name": self.run_name,
            "start_time": self.start_time,
            "end_time": None,
            "targets": [],
            "status": "running",
        }
        self._run_dir: Path | None = None
        self._next_execution_id = 1
        self._next_message_id = 1

        self.vulnerability_found_callback: Callable[[str, str, str, str], None] | None = None

    def set_run_name(self, run_name: str) -> None:
        self.run_name = run_name
        self.run_id = run_name

    def get_run_dir(self) -> Path:
        if self._run_dir is None:
            runs_dir = Path.cwd() / "agent_runs"
            runs_dir.mkdir(exist_ok=True)

            run_dir_name = self.run_name if self.run_name else self.run_id
            self._run_dir = runs_dir / run_dir_name
            self._run_dir.mkdir(exist_ok=True)

        return self._run_dir

    def add_vulnerability_report(
        self,
        title: str,
        content: str,
        severity: str,
    ) -> str:
        report_id = f"vuln-{len(self.vulnerability_reports) + 1:04d}"

        report = {
            "id": report_id,
            "title": title.strip(),
            "content": content.strip(),
            "severity": severity.lower().strip(),
            "timestamp": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
        }

        self.vulnerability_reports.append(report)
        logger.info(f"Added vulnerability report: {report_id} - {title}")

        # Save to disk immediately for real-time parallel updates in Web UI
        self._save_vulnerability_reports_to_disk()

        # Send real-time notification to Telegram/Discord
        self._send_realtime_vulnerability_notification(report)

        if self.vulnerability_found_callback:
            self.vulnerability_found_callback(
                report_id, title.strip(), content.strip(), severity.lower().strip()
            )

        return report_id

    def _send_realtime_vulnerability_notification(self, report: dict[str, Any]) -> None:
        try:
            import requests

            # Locate configuration files
            config_dir = Path.cwd() / "config"
            telegram_token_file = config_dir / "telegram_token.txt"
            telegram_chat_id_file = config_dir / "telegram_chat_id.txt"
            discord_webhook_file = config_dir / "discord_webhook.txt"

            telegram_enabled = False
            telegram_token = None
            telegram_chat_id = None

            discord_enabled = False
            discord_webhook = None

            # Read Telegram config
            if telegram_token_file.exists() and telegram_chat_id_file.exists():
                telegram_token = telegram_token_file.read_text(encoding="utf-8").strip()
                telegram_chat_id = telegram_chat_id_file.read_text(encoding="utf-8").strip()
                if telegram_token and telegram_chat_id:
                    telegram_enabled = True

            # Read Discord config
            if discord_webhook_file.exists():
                discord_webhook = discord_webhook_file.read_text(encoding="utf-8").strip()
                if discord_webhook:
                    discord_enabled = True

            if not telegram_enabled and not discord_enabled:
                return

            # Prepare content preview
            content = report.get("content", "")
            # Strip markdown titles to make preview cleaner
            import re
            clean_content = re.sub(r'(?m)^#\s+.*$', '', content).strip()
            # Truncate content
            preview = clean_content[:400] + "..." if len(clean_content) > 400 else clean_content

            scan_name = self.run_name or self.run_id
            severity = report.get("severity", "info")
            title = report.get("title", "Unknown Vulnerability")

            # 1. Send Telegram Alert
            if telegram_enabled and telegram_token and telegram_chat_id:
                try:
                    tg_msg = (
                        f"🚨 *HADES VULNERABILITY DISCOVERED*\n\n"
                        f"• *Severity:* {severity.upper()}\n"
                        f"• *Title:* {title}\n"
                        f"• *Scan Session:* `{scan_name}`\n\n"
                        f"*Description Summary:*\n{preview}"
                    )
                    requests.post(
                        f"https://api.telegram.org/bot{telegram_token}/sendMessage",
                        json={
                            "chat_id": telegram_chat_id,
                            "text": tg_msg,
                            "parse_mode": "Markdown"
                        },
                        timeout=10
                    )
                except Exception as tg_err:
                    logger.warning(f"Failed to send Telegram real-time alert: {tg_err}")

            # 2. Send Discord Alert
            if discord_enabled and discord_webhook:
                try:
                    color_map = {
                        "critical": 15941470, # Rose Red (#F43F5E)
                        "high": 16347926,     # Orange (#F97316)
                        "medium": 15381256,   # Yellow (#EAB308)
                        "low": 3718648,       # Sky Blue (#38BDF8)
                        "info": 9474192       # Slate Gray
                    }

                    embed = {
                        "title": f"🚨 Vulnerability Discovered: {title}",
                        "color": color_map.get(severity.lower(), 9474192),
                        "fields": [
                            {"name": "Severity", "value": severity.upper(), "inline": True},
                            {"name": "Scan Session", "value": scan_name, "inline": True},
                            {"name": "Description Preview", "value": preview, "inline": False}
                        ],
                        "footer": {
                            "text": "HADES Security Testing Framework"
                        },
                        "timestamp": datetime.utcnow().isoformat() + "Z"
                    }
                    requests.post(
                        discord_webhook,
                        json={"embeds": [embed]},
                        timeout=10
                    )
                except Exception as dc_err:
                    logger.warning(f"Failed to send Discord real-time alert: {dc_err}")

        except Exception as e:
            logger.warning(f"Failed to dispatch real-time vulnerability notification: {e}")

    def _save_vulnerability_reports_to_disk(self) -> None:
        try:
            run_dir = self.get_run_dir()
            vuln_dir = run_dir / "vulnerabilities"
            vuln_dir.mkdir(exist_ok=True)

            severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
            sorted_reports = sorted(
                self.vulnerability_reports,
                key=lambda x: (severity_order.get(x["severity"], 5), x["timestamp"]),
            )

            for report in sorted_reports:
                vuln_file = vuln_dir / f"{report['id']}.md"
                with vuln_file.open("w", encoding="utf-8") as f:
                    f.write(f"# {report['title']}\n\n")
                    f.write(f"**ID:** {report['id']}\n")
                    f.write(f"**Severity:** {report['severity'].upper()}\n")
                    f.write(f"**Found:** {report['timestamp']}\n\n")
                    f.write("## Description\n\n")
                    f.write(f"{report['content']}\n")

            vuln_csv_file = run_dir / "vulnerabilities.csv"
            with vuln_csv_file.open("w", encoding="utf-8", newline="") as f:
                import csv

                fieldnames = ["id", "title", "severity", "timestamp", "file"]
                writer = csv.DictWriter(f, fieldnames=fieldnames)
                writer.writeheader()

                for report in sorted_reports:
                    writer.writerow(
                        {
                            "id": report["id"],
                            "title": report["title"],
                            "severity": report["severity"].upper(),
                            "timestamp": report["timestamp"],
                            "file": f"vulnerabilities/{report['id']}.md",
                        }
                    )
        except Exception as e:
            logger.warning(f"Failed to save vulnerability reports to disk in real-time: {e}")

    def set_final_scan_result(
        self,
        content: str,
        success: bool = True,
    ) -> None:
        self.final_scan_result = content.strip()

        self.scan_results = {
            "scan_completed": True,
            "content": content,
            "success": success,
        }

        logger.info(f"Set final scan result: success={success}")

    def log_agent_creation(
        self, agent_id: str, name: str, task: str, parent_id: str | None = None
    ) -> None:
        agent_data: dict[str, Any] = {
            "id": agent_id,
            "name": name,
            "task": task,
            "status": "running",
            "parent_id": parent_id,
            "created_at": datetime.now(UTC).isoformat(),
            "updated_at": datetime.now(UTC).isoformat(),
            "tool_executions": [],
        }

        self.agents[agent_id] = agent_data

    def log_chat_message(
        self,
        content: str,
        role: str,
        agent_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> int:
        message_id = self._next_message_id
        self._next_message_id += 1

        message_data = {
            "message_id": message_id,
            "content": content,
            "role": role,
            "agent_id": agent_id,
            "timestamp": datetime.now(UTC).isoformat(),
            "metadata": metadata or {},
        }

        self.chat_messages.append(message_data)
        return message_id

    def log_tool_execution_start(self, agent_id: str, tool_name: str, args: dict[str, Any]) -> int:
        execution_id = self._next_execution_id
        self._next_execution_id += 1

        now = datetime.now(UTC).isoformat()
        execution_data = {
            "execution_id": execution_id,
            "agent_id": agent_id,
            "tool_name": tool_name,
            "args": args,
            "status": "running",
            "result": None,
            "timestamp": now,
            "started_at": now,
            "completed_at": None,
        }

        self.tool_executions[execution_id] = execution_data

        if agent_id in self.agents:
            self.agents[agent_id]["tool_executions"].append(execution_id)

        return execution_id

    def update_tool_execution(
        self, execution_id: int, status: str, result: Any | None = None
    ) -> None:
        if execution_id in self.tool_executions:
            self.tool_executions[execution_id]["status"] = status
            self.tool_executions[execution_id]["result"] = result
            self.tool_executions[execution_id]["completed_at"] = datetime.now(UTC).isoformat()

    def update_agent_status(
        self, agent_id: str, status: str, error_message: str | None = None
    ) -> None:
        if agent_id in self.agents:
            self.agents[agent_id]["status"] = status
            self.agents[agent_id]["updated_at"] = datetime.now(UTC).isoformat()
            if error_message:
                self.agents[agent_id]["error_message"] = error_message

    def set_scan_config(self, config: dict[str, Any]) -> None:
        self.scan_config = config

        # Extract targets list in standard format
        targets_list = []
        for target in config.get("targets", []):
            if isinstance(target, dict):
                target_type = target.get("type")
                details = target.get("details", {})
                if target_type == "web_application":
                    targets_list.append(details.get("target_url", ""))
                elif target_type == "repository":
                    targets_list.append(details.get("target_repo", ""))
                elif target_type == "local_code":
                    targets_list.append(details.get("target_path", ""))
            else:
                targets_list.append(str(target))

        self.run_metadata.update(
            {
                "targets": targets_list,
                "user_instructions": config.get("user_instructions", "") or config.get("instruction", ""),
                "template": config.get("template", ""),
                "max_iterations": config.get("max_iterations", 200),
            }
        )

        # Write config metadata to disk immediately at startup
        try:
            run_dir = self.get_run_dir()
            run_config_file = run_dir / "run_config.json"
            import json
            with run_config_file.open("w", encoding="utf-8") as f:
                json.dump(self.run_metadata, f, indent=4)
        except Exception as e:
            logger.warning(f"Failed to save run_config.json at startup: {e}")

    def save_run_data(self) -> None:
        try:
            run_dir = self.get_run_dir()
            self.end_time = datetime.now(UTC).isoformat()

            if self.final_scan_result:
                penetration_test_report_file = run_dir / "penetration_test_report.md"
                with penetration_test_report_file.open("w", encoding="utf-8") as f:
                    f.write("# Security Penetration Test Report\n\n")
                    f.write(
                        f"**Generated:** {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S UTC')}\n\n"
                    )
                    f.write(f"{self.final_scan_result}\n")
                logger.info(
                    f"Saved final penetration test report to: {penetration_test_report_file}"
                )

            if self.vulnerability_reports:
                vuln_dir = run_dir / "vulnerabilities"
                vuln_dir.mkdir(exist_ok=True)

                severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
                sorted_reports = sorted(
                    self.vulnerability_reports,
                    key=lambda x: (severity_order.get(x["severity"], 5), x["timestamp"]),
                )

                for report in sorted_reports:
                    vuln_file = vuln_dir / f"{report['id']}.md"
                    with vuln_file.open("w", encoding="utf-8") as f:
                        f.write(f"# {report['title']}\n\n")
                        f.write(f"**ID:** {report['id']}\n")
                        f.write(f"**Severity:** {report['severity'].upper()}\n")
                        f.write(f"**Found:** {report['timestamp']}\n\n")
                        f.write("## Description\n\n")
                        f.write(f"{report['content']}\n")

                vuln_csv_file = run_dir / "vulnerabilities.csv"
                with vuln_csv_file.open("w", encoding="utf-8", newline="") as f:
                    import csv

                    fieldnames = ["id", "title", "severity", "timestamp", "file"]
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()

                    for report in sorted_reports:
                        writer.writerow(
                            {
                                "id": report["id"],
                                "title": report["title"],
                                "severity": report["severity"].upper(),
                                "timestamp": report["timestamp"],
                                "file": f"vulnerabilities/{report['id']}.md",
                            }
                        )

                logger.info(
                    f"Saved {len(self.vulnerability_reports)} vulnerability reports to: {vuln_dir}"
                )
                logger.info(f"Saved vulnerability index to: {vuln_csv_file}")

            logger.info(f"📊 Essential scan data saved to: {run_dir}")

        except (OSError, RuntimeError):
            logger.exception("Failed to save scan data")

    def _calculate_duration(self) -> float:
        try:
            start = datetime.fromisoformat(self.start_time.replace("Z", "+00:00"))
            if self.end_time:
                end = datetime.fromisoformat(self.end_time.replace("Z", "+00:00"))
                return (end - start).total_seconds()
        except (ValueError, TypeError):
            pass
        return 0.0

    def get_agent_tools(self, agent_id: str) -> list[dict[str, Any]]:
        return [
            exec_data
            for exec_data in self.tool_executions.values()
            if exec_data.get("agent_id") == agent_id
        ]

    def get_real_tool_count(self) -> int:
        return sum(
            1
            for exec_data in self.tool_executions.values()
            if exec_data.get("tool_name") not in ["scan_start_info", "subagent_start_info"]
        )

    def get_total_llm_stats(self) -> dict[str, Any]:
        from hades.tools.agents_graph.agents_graph_actions import _agent_instances

        total_stats = {
            "input_tokens": 0,
            "output_tokens": 0,
            "cached_tokens": 0,
            "cache_creation_tokens": 0,
            "cost": 0.0,
            "requests": 0,
            "failed_requests": 0,
        }

        for agent_instance in _agent_instances.values():
            if hasattr(agent_instance, "llm") and hasattr(agent_instance.llm, "_total_stats"):
                agent_stats = agent_instance.llm._total_stats
                total_stats["input_tokens"] += agent_stats.input_tokens
                total_stats["output_tokens"] += agent_stats.output_tokens
                total_stats["cached_tokens"] += agent_stats.cached_tokens
                total_stats["cache_creation_tokens"] += agent_stats.cache_creation_tokens
                total_stats["cost"] += agent_stats.cost
                total_stats["requests"] += agent_stats.requests
                total_stats["failed_requests"] += agent_stats.failed_requests

        total_stats["cost"] = round(total_stats["cost"], 4)

        return {
            "total": total_stats,
            "total_tokens": total_stats["input_tokens"] + total_stats["output_tokens"],
        }

    def cleanup(self) -> None:
        self.save_run_data()
