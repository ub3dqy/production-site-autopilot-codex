from __future__ import annotations

import html
import json
import shutil
import time
from pathlib import Path
from typing import Any

from .models import RunStatus
from .security import safe_path

REPORT_SCHEMA_VERSION = "1.0"
REQUIRED_KEYS = {
    "schema_version", "run_id", "autopilot_version", "source_commit", "detected_mode",
    "detected_stack", "confidence", "status", "changed_files", "checks", "owner_decisions",
    "blocked", "deferred", "residual_risks", "rollback",
}


def validate_report(data: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    missing = sorted(REQUIRED_KEYS - set(data))
    if missing:
        errors.append("missing keys: " + ", ".join(missing))
    if data.get("schema_version") != REPORT_SCHEMA_VERSION:
        errors.append(f"unsupported schema_version: {data.get('schema_version')!r}")
    try:
        RunStatus(data.get("status"))
    except (ValueError, TypeError):
        errors.append(f"invalid status: {data.get('status')!r}")
    confidence = data.get("confidence")
    if not isinstance(confidence, (int, float)) or not 0 <= confidence <= 1:
        errors.append("confidence must be between 0 and 1")
    for key in ("changed_files", "checks", "owner_decisions", "blocked", "deferred", "residual_risks"):
        if key in data and not isinstance(data[key], list):
            errors.append(f"{key} must be an array")
    return errors


def _markdown(data: dict[str, Any]) -> str:
    def section(title: str, values: list[Any]) -> str:
        rendered = "\n".join(f"- {value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)}" for value in values)
        return f"## {title}\n\n{rendered or '- Нет'}\n"
    return (
        f"# Production Site Autopilot — {data['run_id']}\n\n"
        f"- Статус: **{data['status']}**\n"
        f"- Режим: `{data['detected_mode']}`\n"
        f"- Стек: `{', '.join(data['detected_stack'])}`\n"
        f"- Уверенность: `{data['confidence']:.2f}`\n"
        f"- Версия: `{data['autopilot_version']}`\n\n"
        + section("Что изменено", data["changed_files"]) + "\n"
        + section("Проверки", data["checks"]) + "\n"
        + section("Решения владельца", data["owner_decisions"]) + "\n"
        + section("Заблокировано", data["blocked"]) + "\n"
        + section("Отложено", data["deferred"]) + "\n"
        + section("Остаточные риски", data["residual_risks"]) + "\n## Rollback\n\n"
        + f"```json\n{json.dumps(data['rollback'], ensure_ascii=False, indent=2)}\n```\n"
    )


def _html(data: dict[str, Any]) -> str:
    def list_html(values: list[Any]) -> str:
        return "<ul>" + "".join(f"<li>{html.escape(value if isinstance(value, str) else json.dumps(value, ensure_ascii=False))}</li>" for value in values) + "</ul>"
    return f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Autopilot {html.escape(data['run_id'])}</title></head>
<body><main><h1>Production Site Autopilot</h1>
<p><strong>Статус:</strong> {html.escape(data['status'])}</p>
<p><strong>Режим:</strong> {html.escape(data['detected_mode'])}; <strong>стек:</strong> {html.escape(', '.join(data['detected_stack']))}; <strong>уверенность:</strong> {data['confidence']:.2f}</p>
<h2>Что изменено</h2>{list_html(data['changed_files'])}
<h2>Что проверено</h2>{list_html(data['checks'])}
<h2>Что требует решения</h2>{list_html(data['owner_decisions'] + data['blocked'] + data['deferred'])}
<h2>Остаточные риски</h2>{list_html(data['residual_risks'])}
<h2>Как отменить</h2><pre>{html.escape(json.dumps(data['rollback'], ensure_ascii=False, indent=2))}</pre>
</main></body></html>"""


def write_report(root: Path | str, data: dict[str, Any]) -> dict[str, str]:
    errors = validate_report(data)
    if errors:
        raise ValueError("; ".join(errors))
    root_path = Path(root).resolve()
    state = safe_path(root_path, ".production-site")
    run_dir = safe_path(root_path, state / "runs" / data["run_id"])
    results = safe_path(root_path, state / "results")
    run_dir.mkdir(parents=True, exist_ok=True)
    results.mkdir(parents=True, exist_ok=True)
    data = dict(data)
    data.setdefault("written_at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    json_path = run_dir / "result.json"
    md_path = run_dir / "result.md"
    html_path = run_dir / "result.html"
    json_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(_markdown(data), encoding="utf-8")
    html_path.write_text(_html(data), encoding="utf-8")
    for source, name in ((json_path, "latest.json"), (md_path, "latest.md"), (html_path, "latest.html")):
        shutil.copy2(source, results / name)
    return {"json": str(json_path), "markdown": str(md_path), "html": str(html_path)}
