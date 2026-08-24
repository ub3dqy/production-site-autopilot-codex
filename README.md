# Production Site Autopilot for OpenAI Codex

Инструмент для безопасного аудита, создания, подключения, редизайна, исправления и миграции сайтов с помощью Codex.

> Текущая ветка содержит **v7.2.0-beta.1**. Детерминированные проверки и кроссплатформенный CI находятся в репозитории. Реальные автономные прогоны Codex и production deployment никогда не считаются выполненными без отдельного машинного evidence-файла со статусом `PASS`.

## Что изменено в v7.2

- исходный код, Skill, схемы, тесты и release tooling доступны для просмотра в Git;
- безопасные границы исполняются policy-движком `ALLOW / CONFIRM / DENY`;
- низкая уверенность определения режима автоматически включает `audit-only`;
- файлы проекта рассматриваются как недоверенный ввод и не могут отменить системную политику;
- перед изменениями создаётся baseline, после изменений — manifest, а rollback проверяет конфликты;
- отчёты сохраняются в JSON, Markdown и HTML с версионированной схемой;
- версия задаётся единственным файлом `VERSION`;
- сборка создаёт воспроизводимые ZIP, checksums, SBOM, provenance и test evidence;
- Linux, macOS и Windows проверяются отдельными CI jobs;
- stable-релиз запрещён, пока обязательные live/Windows evidence не имеют статус `PASS`.

## Структура

```text
src/production_site_autopilot/     исполняемый runtime
plugin/                            нативный Skill/plugin layout
installers/                        резервная локальная установка
schemas/                           JSON Schemas
tests/                             детерминированные проверки
fixtures/                          эталонные проекты и угрозы
scripts/                           проверки и release tooling
docs/                              архитектура, профили и threat model
evidence/                          машинные статусы внешних проверок
.github/workflows/                 CI, security, live-eval и release
```

## Быстрый запуск

Скопируйте каталог `plugin/skills/production-site-autopilot` в `.codex/skills/production-site-autopilot` выбранного проекта либо используйте резервный установщик без административных прав:

```powershell
powershell -ExecutionPolicy Bypass -File installers/install.ps1 -ProjectPath "C:\path\to\site"
```

```bash
./installers/install.sh /path/to/site
```

После установки откройте проект в Codex и напишите:

```text
Доведи этот сайт до production-ready состояния. Сначала выполни безопасный preflight, сам выбери режим и стек, затем сделай всю разрешённую работу и сохрани evidence.
```

## Локальная проверка

```bash
python scripts/run_checks.py
PYTHONPATH=src python -m production_site_autopilot doctor .
PYTHONPATH=src python -m production_site_autopilot detect .
```

Результаты работы сохраняются в `.production-site/results/latest.{json,md,html}` и `.production-site/runs/<run-id>/`.

## Безопасные границы

Автоматически разрешены чтение, локальные тесты, локальная сборка, отчётность и обратимые изменения внутри workspace. Подтверждение владельца требуется для удаления данных/страниц, установки зависимостей, сетевых действий, изменения домена, аналитики, CI, push и любого deployment. Покупки, вывод секретов, обход policy, force-push и запись вне workspace запрещены.

Один checkpoint может содержать один **консолидированный пакет решений**, но неизвестные юридические, коммерческие и брендовые решения не подменяются догадками.

## Production-ready профили

Поддерживаются профили `MARKETING_SITE`, `WEB_APPLICATION`, `COMMERCE` и `REGULATED_OR_HIGH_RISK`. Последний по умолчанию работает только в режиме аудита. Статусы результата: `AUDIT_COMPLETE`, `READY_FOR_REVIEW`, `READY_FOR_PREVIEW`, `READY_FOR_DEPLOYMENT`, `READY_WITH_DEFERRED_ITEMS`, `BLOCKED`, `FAILED`.

## Честность evidence

Файлы `evidence/live-codex.json` и `evidence/windows-native.json` содержат только `PASS`, `FAIL` или `NOT_RUN`. `NOT_RUN` не преобразуется в PASS и блокирует stable release, когда проверка объявлена обязательной.

Лицензия явно разрешает скачивание, установку и локальное использование продукта, сохраняя ограничения на перепродажу и распространение. Политика сообщения об уязвимостях находится в [SECURITY.md](SECURITY.md).
