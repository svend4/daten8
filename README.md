# daten8 — Classified Ads Indexer (мониторинг и индексация объявлений)

Проект системы автоматического сбора, классификации, хранения и мониторинга объявлений о бесплатной раздаче вещей с досок объявлений (например, eBay Kleinanzeigen).

> **Состояние ветки `main`:** в основной ветке `main` находятся только `README.md` и `LICENSE`. Исходный код на Python, конфигурационные шаблоны и документация проекта расположены в неслитой ветке [`claude/classified-ads-indexer-egVtD`](../../tree/claude/classified-ads-indexer-egVtD).

## Возможности (по ветке `claude/classified-ads-indexer-egVtD`)

- **Краулер (`src/crawler/`)**: базовый класс `BaseCrawler` (ограничение частоты запросов, повторы с экспоненциальной задержкой, разбор локации) и парсер `EbayCrawler` (BeautifulSoup + `lxml`) для сбора списков и карточек объявлений.
- **Классификация (`src/classifier/text_classifier.py`)**: класс `TextClassifier` на базе `TfidfVectorizer` и `MultinomialNB` (`scikit-learn`) с порогом уверенности и извлечением признаков (`extract_features`: состояние предмета, бренд, размеры).
- **Хранение и полнотекстовый поиск (`src/database/`)**: `DatabaseManager` и схема SQLite (`schema.sql`) с таблицами `ads`, `images`, `categories`, `subscriptions`, `notifications`, `crawler_state`, `crawler_logs`, `clusters`, `ad_clusters`, триггерным полнотекстовым индексом `ads_fts` (SQLite FTS5) и представлениями (`active_ads`, `ads_with_location`, `recent_ads`).
- **Уведомления (`src/notifier/`)**:
  - `RSSGenerator` (`rss_generator.py`, библиотека `feedgen`) — генерация RSS-лент по категориям, городам и гео-координатам;
  - `EmailSender` (`email_sender.py`, `smtplib`) — отправка HTML-дайджестов и проверка SMTP-соединения.

## Структура проекта

### Ветка `main`

- `LICENSE` — текст лицензии GNU Affero General Public License v3.
- `README.md` — описание проекта.

### Ветка `claude/classified-ads-indexer-egVtD`

```text
├── .gitignore
├── README.md
├── requirements.txt
├── config/
│   ├── config.example.yaml        # Шаблон основных настроек (БД, краулер, ML, RSS, SMTP, геолокация)
│   ├── sources.yaml               # Настройки источников (ebay_kleinanzeigen активен; craigslist, kleinanzeigen, shpock, nebenan, facebook_marketplace отключены)
│   └── subscriptions.example.yaml # Шаблон подписок на уведомления
├── docs/
│   ├── ARCHITECTURE.md
│   ├── IMPLEMENTATION.md
│   └── PROJECT_OVERVIEW.md
└── src/
    ├── __init__.py
    ├── crawler/
    │   ├── __init__.py
    │   ├── base_crawler.py
    │   └── ebay_crawler.py
    ├── classifier/
    │   ├── __init__.py
    │   └── text_classifier.py
    ├── database/
    │   ├── __init__.py
    │   ├── db_manager.py
    │   └── schema.sql
    └── notifier/
        ├── __init__.py
        ├── rss_generator.py
        └── email_sender.py
```

## Технологический стек и установка

По `requirements.txt` из ветки `claude/classified-ads-indexer-egVtD`:

- **Язык:** Python >= 3.11
- **Библиотеки:** `requests==2.31.0`, `beautifulsoup4==4.12.3`, `lxml==5.1.0`, `scikit-learn==1.4.0`, `numpy==1.26.3`, `joblib==1.3.2`, `feedgen==1.0.0`, `PyYAML==6.0.1`, `python-dotenv==1.0.0`, `python-dateutil==2.8.2`, `loguru==0.7.2`
- **Тестирование и стиль кода:** `pytest==7.4.4`, `pytest-cov==4.1.0`, `black==24.1.1`, `flake8==7.0.0` (опциональные зависимости в `requirements.txt` закомментированы: `scrapy`, `spacy`, `langdetect`, `psycopg2-binary`, `alembic`, `geopy`, `fastapi`, `uvicorn`, `pydantic`, `mypy`).

Подготовка окружения на ветке `claude/classified-ads-indexer-egVtD`:

```bash
git checkout claude/classified-ads-indexer-egVtD
python -m venv venv
# Linux/Mac: source venv/bin/activate
# Windows:   venv\Scripts\activate
pip install -r requirements.txt
cp config/config.example.yaml config/config.yaml
```

> **Примечание:** в текущем составе ветки `claude/classified-ads-indexer-egVtD` реализованы модули библиотеки (`src/crawler`, `src/classifier`, `src/database`, `src/notifier`), а отдельные CLI-точки входа (такие как `src/crawler/run.py` или `src/notifier/generate_rss.py`, упоминаемые в черновике README ветки) и каталог `tests/` пока не созданы.

## Ветки репозитория

- `main` — защищённая основная ветка (`LICENSE`, `README.md`).
- `claude/classified-ads-indexer-egVtD` — неслитая ветка с архитектурой, конфигурациями (`config/`), документацией (`docs/`) и Python-модулями (`src/`).
- `codex/readme-overview-20261118` — неслитая ветка с открытым draft PR [#1](../../pull/1) («Add concise project README»), содержащая краткую заглушку README по описанию репозитория.

## Лицензия

В ветке `main` проект распространяется под лицензией **GNU Affero General Public License v3** (см. файл `LICENSE`). В `README.md` ветки `claude/classified-ads-indexer-egVtD` упоминалась лицензия MIT.
