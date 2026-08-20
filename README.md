# Production Site Autopilot for OpenAI Codex

Универсальный инструмент для создания, подключения, аудита, редизайна, исправления, миграции и доведения сайтов до production с помощью Codex.

## Две редакции

| Редакция | Назначение |
|---|---|
| **User Edition** | Одна точка входа, автоматический выбор режима и минимальное участие пользователя |
| **Engineering Edition** | Полный Skill, contracts, gates, stack playbooks, validators, tests и release tooling |

После публикации релиза обе редакции доступны на странице [Releases](../../releases/tag/v7.1.0).

## Быстрый запуск User Edition

### Windows

1. Скачайте `production-site-autopilot-codex-user-v7.1.0.zip`.
2. Распакуйте архив.
3. Запустите `START_SITE_AUTOPILOT_WINDOWS.cmd`.
4. Выберите каталог проекта.

После установки можно открыть любой проект в Codex и написать:

```text
Создай или доведи этот сайт до production. Сам всё проанализируй, исправь и проверь.
```

Autopilot сам определяет режим и стек, создаёт безопасную конфигурацию, выполняет доступную работу, повторяет проверки и сохраняет итог в:

```text
.production-site/results/latest.md
.production-site/results/latest.json
```

## Содержимое репозитория

```text
user/          # распакованная пользовательская редакция v7.1.0
engineering/   # распакованная инженерная редакция v7.1.0
.github/       # автоматическая проверка и публикация релиза
SHA256SUMS     # контрольные суммы релизных ZIP
```

## Контрольные суммы v7.1.0

```text
90a118d52020b2307c8447ea81ad6cd520492d255a274440adaa0cf03d257886  production-site-autopilot-codex-user-v7.1.0.zip
97666e9ba94e41a7c4cd103d3023bf1fd7c243f15ef43dec96fa45822dfaaac6  production-site-autopilot-codex-engineering-v7.1.0.zip
```

## Проверенный статус

- artifact coverage: **80/80 PASS**;
- configuration scenarios: **18/18 PASS**;
- validator regression tests: **14/14 PASS**;
- Autopilot deterministic tests: **9/9 PASS**;
- UX и lifecycle checks: **36/36 PASS**;
- live Codex behavioral suite: **NOT_RUN**;
- native Windows runtime в исходной Linux-среде сборки: **NOT_RUN**.

## Безопасные границы

Без отдельного решения пользователя Autopilot не меняет URL, домен или основной стек, не удаляет страницы и данные, не публикует неподтверждённые claims, не включает tracking, не покупает услуги и не выполняет production deployment. Блокирующие решения объединяются максимум в один вопрос.
