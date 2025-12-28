# Архитектура системы Classified Ads Indexer

## Обзор

Система построена по модульному принципу и состоит из пяти основных компонентов, взаимодействующих через общую базу данных.

## Компоненты системы

### 1. Crawler Module (Модуль сбора данных)

**Назначение:** Автоматический сбор объявлений с различных досок объявлений.

**Основные функции:**
- Периодическое сканирование целевых сайтов по расписанию (cron)
- Извлечение структурированных данных из HTML
- Обнаружение и фильтрация дубликатов
- Обработка изображений (загрузка и хранение)
- Управление состоянием (tracking последней обработанной страницы)

**Технологии:**
- `requests` + `Beautiful Soup` — для простых сайтов
- `Scrapy` — для сложных сайтов с JavaScript (опционально)
- `lxml` — быстрый парсинг XML/HTML

**Структура данных (извлекаемая информация):**
```python
{
    "id": "unique_id",
    "source": "ebay_kleinanzeigen",
    "url": "https://...",
    "title": "Отдам принтер HP бесплатно",
    "description": "Рабочий принтер...",
    "location": {
        "city": "Berlin",
        "district": "Kreuzberg",
        "postal_code": "10999",
        "address": "..."
    },
    "posted_date": "2025-12-28T10:30:00",
    "images": ["url1", "url2"],
    "contact": {
        "type": "email/phone",
        "value": "..."
    },
    "raw_html": "..."  # для последующего анализа
}
```

**Режимы работы:**
- **Incremental** — сканирование только новых объявлений
- **Full** — полное сканирование (для инициализации)
- **Update** — обновление существующих объявлений

**Обработка ошибок:**
- Retry механизм с экспоненциальной задержкой
- Ротация User-Agent для избежания блокировок
- Соблюдение robots.txt
- Rate limiting (задержки между запросами)

---

### 2. Data Pipeline (Конвейер обработки данных)

**Назначение:** Очистка, нормализация и обогащение собранных данных.

**Этапы обработки:**

1. **Очистка текста:**
   - Удаление HTML-тегов
   - Нормализация пробелов и переносов строк
   - Удаление спецсимволов
   - Исправление кодировок

2. **Нормализация местоположения:**
   - Парсинг адресов
   - Стандартизация названий городов/районов
   - Извлечение координат (если доступно)
   - Геокодирование (опционально, через OpenStreetMap Nominatim)

3. **Извлечение метаданных:**
   - Определение языка текста
   - Извлечение дат и времени
   - Парсинг контактной информации

4. **Дедупликация:**
   - Хеширование контента (SimHash, MinHash)
   - Поиск похожих объявлений
   - Группировка дубликатов

**Технологии:**
- `re` (regex) — парсинг паттернов
- `ftfy` — исправление кодировок
- `langdetect` — определение языка
- `geopy` — геокодирование (опционально)

---

### 3. Classifier Module (Модуль классификации)

**Назначение:** Автоматическая категоризация и извлечение характеристик объявлений.

**Функции:**

#### 3.1. Классификация по категориям

**Категории:**
- Компьютеры и электроника
- Мебель
- Одежда и аксессуары
- Книги и медиа
- Спорт и хобби
- Детские товары
- Бытовая техника
- Строительство и ремонт
- Сад и растения
- Прочее

**Метод классификации:**
- **TF-IDF** (Term Frequency-Inverse Document Frequency) для векторизации текста
- **Naive Bayes** или **SVM** для классификации
- **Точность:** ~85-90% (достаточно для задачи)

**Обучение модели:**
```python
# Пример пайплайна
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB

classifier = Pipeline([
    ('tfidf', TfidfVectorizer(max_features=5000, ngram_range=(1, 2))),
    ('clf', MultinomialNB())
])
```

**Данные для обучения:**
- Ручная разметка ~1000-2000 объявлений (one-time)
- Активное обучение (пользователи могут корректировать категории)

#### 3.2. Кластеризация

**Цель:** Группировка похожих объявлений.

**Метод:**
- **K-Means** или **DBSCAN** для кластеризации векторов TF-IDF
- Параметры: расстояние (cosine similarity)

**Применение:**
- Обнаружение массовых раздач (например, распродажа магазина)
- Агрегация похожих предметов
- Рекомендации ("похожие объявления")

#### 3.3. Извлечение характеристик

**Извлекаемые атрибуты:**
- Состояние (новое, б/у, требует ремонта)
- Размеры (если указаны)
- Бренд/производитель
- Модель
- Цвет
- Материал

**Методы:**
- Регулярные выражения для структурированных данных
- NER (Named Entity Recognition) — для извлечения брендов
- Словари и онтологии

**Технологии:**
- `scikit-learn` — ML алгоритмы
- `spaCy` (опционально) — NER для немецкого/английского языка

---

### 4. Database Module (Модуль базы данных)

**Назначение:** Хранение и управление данными объявлений.

**Схема базы данных:**

#### Таблица: `ads` (объявления)
```sql
CREATE TABLE ads (
    id TEXT PRIMARY KEY,
    source TEXT NOT NULL,
    url TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    category TEXT,
    city TEXT,
    district TEXT,
    postal_code TEXT,
    latitude REAL,
    longitude REAL,
    posted_date DATETIME,
    crawled_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'active',  -- active, expired, deleted
    hash TEXT,  -- для дедупликации
    FULLTEXT INDEX (title, description)
);
```

#### Таблица: `images` (изображения)
```sql
CREATE TABLE images (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ad_id TEXT REFERENCES ads(id) ON DELETE CASCADE,
    url TEXT,
    local_path TEXT,
    downloaded BOOLEAN DEFAULT 0
);
```

#### Таблица: `categories` (категории)
```sql
CREATE TABLE categories (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    parent_id INTEGER REFERENCES categories(id),
    keywords TEXT  -- для улучшения классификации
);
```

#### Таблица: `subscriptions` (подписки пользователей)
```sql
CREATE TABLE subscriptions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email TEXT,
    category TEXT,
    city TEXT,
    district TEXT,
    keywords TEXT,  -- JSON array
    radius_km REAL,
    created_date DATETIME DEFAULT CURRENT_TIMESTAMP
);
```

#### Таблица: `notifications` (отправленные уведомления)
```sql
CREATE TABLE notifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subscription_id INTEGER REFERENCES subscriptions(id),
    ad_id TEXT REFERENCES ads(id),
    sent_date DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(subscription_id, ad_id)  -- не дублировать уведомления
);
```

**Выбор БД:**
- **SQLite** — для небольших инсталляций (до 100k объявлений)
- **PostgreSQL** — для крупных инсталляций, поддержка полнотекстового поиска

**Индексы:**
```sql
CREATE INDEX idx_ads_city ON ads(city);
CREATE INDEX idx_ads_category ON ads(category);
CREATE INDEX idx_ads_posted_date ON ads(posted_date DESC);
CREATE INDEX idx_ads_location ON ads(latitude, longitude);  -- для гео-поиска
```

---

### 5. Notifier Module (Модуль уведомлений)

**Назначение:** Генерация RSS/Atom лент и отправка email-уведомлений.

#### 5.1. RSS/Atom Generator

**Структура RSS лент:**
```
/rss/all.xml                          # Все объявления
/rss/{city}/all.xml                   # Все объявления в городе
/rss/{city}/{category}.xml            # Категория в городе
/rss/{city}/{district}/{category}.xml # Категория в районе
/rss/search?q={keywords}&city={city}  # Поиск по ключевым словам
```

**Формат RSS 2.0:**
```xml
<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>Бесплатные объявления - Компьютеры - Берлин</title>
    <link>https://yourserver.com/rss/berlin/computers</link>
    <description>Бесплатные компьютеры в Берлине</description>
    <item>
      <title>Отдам принтер HP LaserJet</title>
      <link>https://source.com/ad/12345</link>
      <description>Рабочий принтер, б/у, самовывоз из Kreuzberg</description>
      <category>Компьютеры</category>
      <pubDate>Sat, 28 Dec 2025 10:30:00 +0100</pubDate>
      <guid>ad_12345</guid>
      <geo:lat>52.5200</geo:lat>
      <geo:long>13.4050</geo:long>
    </item>
  </channel>
</rss>
```

**Технологии:**
- `feedgen` — генерация RSS/Atom
- Статическая генерация (файлы обновляются по cron)
- Опционально: динамическая генерация через Web API

**Частота обновления:**
- Каждые 15-60 минут (настраивается)

#### 5.2. Email Notifier

**Функции:**
- Проверка новых объявлений, соответствующих подпискам
- Формирование HTML-писем с подборкой объявлений
- Отправка дайджестов (ежедневно или при появлении новых объявлений)

**Формат письма:**
```
Тема: Новые бесплатные объявления в Берлине (3 шт.)

Здравствуйте!

Найдено 3 новых объявления по вашим критериям:

1. Принтер HP LaserJet
   Категория: Компьютеры
   Расположение: Berlin, Kreuzberg
   Описание: Рабочий принтер, б/у, самовывоз
   Ссылка: https://...

2. ...
```

**Технологии:**
- `smtplib` — отправка через SMTP
- `email.mime` — формирование HTML-писем
- Поддержка Gmail, Mailgun, SendGrid и др.

**Ограничения:**
- Максимум 1 письмо в день на подписку (опционально)
- Группировка объявлений в дайджесты

---

## Поток данных

```
1. Crawler
   └─► Сырые данные → Database (raw)

2. Data Pipeline
   └─► Очистка → Нормализация → Database (cleaned)

3. Classifier
   └─► Классификация → Кластеризация → Database (categorized)

4. Notifier (по расписанию)
   ├─► RSS Generator → Статические RSS файлы
   └─► Email Sender → SMTP → Пользователи

5. API (опционально)
   └─► Web интерфейс для поиска и просмотра
```

## Масштабируемость

### Для малых инсталляций (до 10k объявлений)
- SQLite
- Один сервер
- Cron для планирования задач

### Для средних инсталляций (10k-100k объявлений)
- PostgreSQL
- Celery для фоновых задач
- Redis для кеширования

### Для крупных инсталляций (100k+ объявлений)
- PostgreSQL с партиционированием
- Elasticsearch для полнотекстового поиска
- Distributed crawling (Scrapy + Redis)
- CDN для RSS/статических файлов

## Безопасность

1. **Rate Limiting:** Ограничение частоты запросов к источникам
2. **User-Agent Rotation:** Избежание блокировок
3. **Robots.txt Compliance:** Соблюдение правил сайтов
4. **Data Privacy:** Хранение минимума персональных данных
5. **Email Validation:** Проверка email перед отправкой
6. **CAPTCHA Handling:** Обработка защиты (если требуется)

## Мониторинг и логирование

- **Логи:** Structured logging (JSON format)
- **Метрики:**
  - Количество собранных объявлений в день
  - Точность классификации
  - Время работы краулера
  - Количество отправленных уведомлений
- **Алерты:**
  - Сбой краулера
  - Изменение структуры сайта-источника
  - Превышение лимита ошибок

## Конфигурация

Все параметры системы настраиваются через YAML-файлы:

- `config/sources.yaml` — настройка источников
- `config/classifier.yaml` — параметры ML-моделей
- `config/notifier.yaml` — настройка RSS и email
- `config/database.yaml` — подключение к БД
- `config/schedule.yaml` — расписание задач
