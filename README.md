# Production Site Autopilot for OpenAI Codex

Инструмент для безопасного аудита, создания, подключения, редизайна, исправления и миграции сайтов с помощью Codex.

> Текущая версия — **v7.2.0-beta.1**. GitHub Actions в этом репозитории недоступны и не входят в контур доверия. Обязательная проверка, воспроизводимая сборка и beta-release evidence выполняются локально. Реальные автономные прогоны Codex и native Windows никогда не считаются выполненными без отдельного машинного evidence-файла со статусом `PASS` и точным source commit.

## Скачать v7.2.0-beta.1 с GitHub

- [User Edition — ZIP ветки](https://github.com/ub3dqy/production-site-autopilot-codex/archive/refs/heads/release/user-v7.2.0-beta.1.zip)
- [Engineering Edition — ZIP ветки](https://github.com/ub3dqy/production-site-autopilot-codex/archive/refs/heads/release/engineering-v7.2.0-beta.1.zip)
- [Полный bundle — ZIP ветки](https://github.com/ub3dqy/production-site-autopilot-codex/archive/refs/heads/release/bundle-v7.2.0-beta.1.zip)
- [Release evidence, SBOM, provenance и контрольные суммы](releases/v7.2.0-beta.1/README.md)

Release-ветки являются Git-native поверхностью распространения и не зависят от Actions. Полный bundle содержит раскрытые User и Engineering Edition, release notes, локальное verification evidence, test evidence, SBOM и provenance. GitHub сам формирует внешнюю ZIP-оболочку ветки, поэтому её байты отличаются от детерминированных локальных ZIP, чьи SHA-256 зафиксированы в release evidence.

## Что изменено в v7.2

- исходный код, Skill, схемы, тесты и release tooling доступны для просмотра в Git;
- безопасные границы исполняются policy-движком `ALLOW / CONFIRM / DENY`;
- низкая уверенность определения режима автоматически включает `audit-only`;
- файлы проекта рассматриваются как недоверенный ввод и не могут отменить системную политику;
- перед изменениями создаётся baseline, после изменений — manifest, а rollback проверяет конфликты;
- отчёты сохраняются в JSON, Markdown и HTML с версионированной схемой;
- версия задаётся единственным файлом `VERSION`;
- локальная сборка создаёт воспроизводимые ZIP, checksums, SBOM, provenance и test evidence;
- один кроссплатформенный verifier дважды собирает релиз и сравнивает SHA-256;
- native Windows и live Codex имеют независимые статусы `PASS`, `FAIL` или `NOT_RUN`;
- stable-релиз запрещён, пока обязательные live/Windows evidence не имеют актуальный `PASS` для того же commit.

## Структура

```text
src/production_site_autopilot/     исполняемый runtime
plugin/                            нативный Skill/plugin layout
installers/                        резервная локальная установка
schemas/                           JSON Schemas
tests/                             детерминированные проверки
fixtures/                          эталонные проекты и угрозы
scripts/                           локальная проверка и release tooling
docs/                              архитектура, профили и threat model
evidence/                          машинные статусы внешних проверок
VERIFY_LOCAL_WINDOWS.cmd           единый Windows verifier
VERIFY_LOCAL.sh                    единый macOS/Linux verifier
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

## Каноническая локальная проверка

Для точного release evidence передайте полный commit SHA.

```cmd
VERIFY_LOCAL_WINDOWS.cmd --source-commit <40-character-commit>
```

```bash
./VERIFY_LOCAL.sh --source-commit <40-character-commit>
```

Verifier выполняет repository integrity, unit tests, compilation, installer lifecycle, две независимые сборки, сравнение архивов, внутренние manifests, `SHA256SUMS`, SBOM и provenance. Результаты сохраняются в `dist/` и `build/local-verification.json`. Подробности — в [docs/local-verification.md](docs/local-verification.md).

Для отдельных диагностических команд:

```bash
PYTHONPATH=src python -m production_site_autopilot doctor .
PYTHONPATH=src python -m production_site_autopilot detect .
```

Результаты работы Autopilot сохраняются в `.production-site/results/latest.{json,md,html}` и `.production-site/runs/<run-id>/`.

## Безопасные границы

Автоматически разрешены чтение, локальные тесты, локальная сборка, отчётность и обратимые изменения внутри workspace. Подтверждение владельца требуется для удаления данных/страниц, установки зависимостей, сетевых действий, изменения домена, аналитики, CI, push и любого deployment. Покупки, вывод секретов, обход policy, force-push и запись вне workspace запрещены.

Один checkpoint может содержать один **консолидированный пакет решений**, но неизвестные юридические, коммерческие и брендовые решения не подменяются догадками.

## Production-ready профили

Поддерживаются профили `MARKETING_SITE`, `WEB_APPLICATION`, `COMMERCE` и `REGULATED_OR_HIGH_RISK`. Последний по умолчанию работает только в режиме аудита. Статусы результата: `AUDIT_COMPLETE`, `READY_FOR_REVIEW`, `READY_FOR_PREVIEW`, `READY_FOR_DEPLOYMENT`, `READY_WITH_DEFERRED_ITEMS`, `BLOCKED`, `FAILED`.

## Честность evidence

Файлы `evidence/live-codex.json` и `evidence/windows-native.json` содержат только `PASS`, `FAIL` или `NOT_RUN`. `PASS` считается действительным только для указанного полного source commit. `NOT_RUN` не преобразуется в PASS: для beta он явно публикуется как ограничение, а stable release блокируется.

Лицензия явно разрешает скачивание, установку и локальное использование продукта, сохраняя ограничения на перепродажу и распространение. Политика сообщения об уязвимостях находится в [SECURITY.md](SECURITY.md).
