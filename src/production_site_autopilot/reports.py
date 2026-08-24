from __future__ import annotations

import html
import json
import os
import re
import shutil
import time
import uuid
from pathlib import Path
from typing import Any

from .models import RunStatus
from .security import safe_path

REPORT_SCHEMA_VERSION = "1.0"
RUN_ID_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
CHECK_STATUSES = {"PASS", "FAIL", "NOT_RUN"}
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
    run_id = data.get("run_id")
    if not isinstance(run_id, str) or not RUN_ID_RE.fullmatch(run_id):
        errors.append("run_id has an unsafe or invalid format")
    try:
        status = RunStatus(data.get("status"))
    except (ValueError, TypeError):
        status = None
        errors.append(f"invalid status: {data.get('status')!r}")
    confidence = data.get("confidence")
    if not isinstance(confidence, (int, float)) or isinstance(confidence, bool) or not 0 <= confidence <= 1:
        errors.append("confidence must be a number between 0 and 1")
    for key in ("changed_files", "checks", "owner_decisions", "blocked", "deferred", "residual_risks"):
        if key in data and not isinstance(data[key], list):
            errors.append(f"{key} must be an array")
    checks = data.get("checks", []) if isinstance(data.get("checks"), list) else []
    for index, check in enumerate(checks):
        if not isinstance(check, dict):
            errors.append(f"checks[{index}] must be an object")
            continue
        if not isinstance(check.get("id"), str) or not check["id"]:
            errors.append(f"checks[{index}].id is required")
        if check.get("status") not in CHECK_STATUSES:
            errors.append(f"checks[{index}].status must be PASS, FAIL, or NOT_RUN")
        if check.get("status") == "PASS" and not check.get("evidence"):
            errors.append(f"checks[{index}] cannot be PASS without evidence")
    if status is RunStatus.READY_FOR_DEPLOYMENT:
        if data.get("blocked") or data.get("deferred"):
            errors.append("READY_FOR_DEPLOYMENT cannot contain blocked or deferred work")
        if any(check.get("status") != "PASS" for check in checks if isinstance(check, dict)):
            errors.append("READY_FOR_DEPLOYMENT requires all recorded checks to PASS")
    if status in {RunStatus.READY_FOR_PREVIEW, RunStatus.READY_FOR_DEPLOYMENT}:
        if any(check.get("status") == "FAIL" for check in checks if isinstance(check, dict)):
            errors.append(f"{status.value} cannot contain a failed check")
    return errors


def _atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp-" + uuid.uuid4().hex)
    temporary.write_text(text, encoding="utf-8")
    os.replace(temporary, path)


def _render_item(value: Any) -> str:
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, sort_keys=True)


def _markdown(data: dict[str, Any]) -> str:
    def section(title: str, values: list[Any]) -> str:
        rendered = "\n".join(f"- {_render_item(value)}" for value in values)
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
        items = "".join(f"<li>{html.escape(_render_item(value))}</li>" for value in values)
        return f"<ul>{items or '<li>Нет</li>'}</ul>"
    return f"""<!doctype html>
<html lang="ru"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'">
<title>Autopilot {html.escape(data['run_id'])}</title><style>body{{font-family:system-ui,sans-serif;max-width:960px;margin:2rem auto;padding:0 1rem;line-height:1.5}}pre{{white-space:pre-wrap;overflow-wrap:anywhere}}</style></head>
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
    runs_root = safe_path(root_path, state / "runs")
    run_dir = safe_path(runs_root, runs_root / data["run_id"])
    results = safe_path(root_path, state / "results")
    run_dir.mkdir(parents=True, exist_ok=True)
    results.mkdir(parents=True, exist_ok=True)
    rendered = dict(data)
    rendered.setdefault("written_at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    json_path = run_dir / "result.json"
    md_path = run_dir / "result.md"
    html_path = run_dir / "result.html"
    _atomic_write(json_path, json.dumps(rendered, ensure_ascii=False, indent=2) + "\n")
    _atomic_write(md_path, _markdown(rendered))
    _atomic_write(html_path, _html(rendered))
    for source, name in ((json_path, "latest.json"), (md_path, "latest.md"), (html_path, "latest.html")):
        temporary = results / (name + ".tmp-" + uuid.uuid4().hex)
        shutil.copy2(source, temporary)
        os.replace(temporary, results / name)
    return {"json": str(json_path), "markdown": str(md_path), "html": str(html_path)}
