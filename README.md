# Production Site Autopilot for OpenAI Codex

Инструмент для безопасного аудита, создания, подключения, редизайна, исправления и миграции сайтов с помощью Codex.

> Текущая версия исходников — **v7.2.0-beta.1**. Детерминированные проверки находятся в репозитории и воспроизводятся в CI. Реальный автономный прогон Codex или production deployment никогда не считается выполненным без отдельного машинного evidence-файла со статусом `PASS` для текущего commit.

## Что исправлено в v7.2

- исходный код, Skill, схемы, fixtures, тесты, установщики и release tooling доступны для просмотра в Git;
- удалены Base64/xz bundle, materializer, зависимость от постороннего репозитория и force-push publisher;
- безопасные границы исполняются policy-движком `ALLOW / CONFIRM / DENY`;
- низкая уверенность определения существующего проекта автоматически включает `audit-only`, но пустой каталог корректно остаётся `greenfield`;
- содержимое проекта считается недоверенным вводом и не может отменить policy;
- пути ограничены выбранным workspace, symlink/reparse-point escape отклоняется;
- перед изменениями обязателен baseline, после изменений создаётся manifest, а rollback проверяет конфликты и целостность backup;
- секретоподобные и слишком большие файлы не копируются в evidence, а raw Git diff с потенциальными секретами не сохраняется;
- отчёты создаются в JSON, Markdown и HTML по версионированной схеме;
- production-ready формализован через профили и итоговые статусы;
- Linux, macOS и Windows проверяются в CI;
- release содержит воспроизводимые ZIP, SHA-256, test evidence, CycloneDX SBOM и provenance;
- stable release блокируется, пока обязательные live/Windows evidence не имеют `PASS` для того же commit.

## Структура

```text
src/production_site_autopilot/     исполняемый runtime
plugin/                            Skill и метаданные поставки
installers/                        install/update/doctor/rollback/uninstall
schemas/                           JSON Schemas
tests/                             детерминированные проверки
fixtures/ и evals/                 эталонные проекты и behavioral contracts
scripts/                           verification и release tooling
docs/                              архитектура, профили, threat model
evidence/                          PASS / FAIL / NOT_RUN внешних проверок
.github/workflows/                 CI, CodeQL, live eval и release
```

## Установка в проект

### Windows

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File installers\install.ps1 -Action Install -ProjectPath "C:\path\to\site"
```

Либо:

```cmd
installers\START_SITE_AUTOPILOT_WINDOWS.cmd "C:\path\to\site"
```

### macOS / Linux

```bash
sh installers/install.sh install /path/to/site
```

Skill устанавливается локально в:

```text
<project>/.codex/skills/production-site-autopilot/
```

Административные права не нужны. Повторная установка работает как update и сохраняет предыдущую управляемую копию для installer rollback.

После установки откройте проект в Codex и напишите:

```text
Доведи этот сайт до production-ready состояния. Сначала выполни безопасный preflight, сам определи режим и стек, затем сделай всю разрешённую работу и сохрани evidence.
```

## Проверка репозитория

```bash
PYTHONPATH=src python scripts/run_checks.py
PYTHONPATH=src python -m production_site_autopilot doctor .
PYTHONPATH=src python -m production_site_autopilot detect .
python scripts/build_release.py --output-dir dist
```

Результаты работы проекта сохраняются в:

```text
.production-site/results/latest.json
.production-site/results/latest.md
.production-site/results/latest.html
.production-site/runs/<run-id>/
```

## Безопасные границы

Автоматически разрешены чтение, локальные тесты, локальная сборка, отчётность и обратимые изменения внутри workspace после создания baseline. Подтверждение владельца требуется для удаления, установки зависимостей, сетевых действий, изменения домена, аналитики, CI, push, database migration и deployment. Покупки, вывод/отправка секретов, обход policy, запись вне workspace, force-push и переписывание истории запрещены.

Один checkpoint содержит максимум один **консолидированный пакет решений**, но неизвестные юридические, коммерческие, брендовые и продуктовые решения не подменяются догадками. Независимая безопасная работа продолжается.

## Production-ready профили

- `MARKETING_SITE`
- `WEB_APPLICATION`
- `COMMERCE`
- `REGULATED_OR_HIGH_RISK` — только аудит, пока не подключена отдельная доменная policy

Итоговые статусы:

```text
AUDIT_COMPLETE
READY_FOR_REVIEW
READY_FOR_PREVIEW
READY_FOR_DEPLOYMENT
READY_WITH_DEFERRED_ITEMS
BLOCKED
FAILED
```

## Честность evidence

`PASS` допустим только при наличии evidence и привязки к проверяемому commit. `NOT_RUN` не преобразуется в PASS. Beta может публиковаться с явно указанным `NOT_RUN`; stable — нет.

Лицензия явно разрешает скачивание, установку и локальное использование. Уязвимости сообщаются по правилам [SECURITY.md](SECURITY.md).
