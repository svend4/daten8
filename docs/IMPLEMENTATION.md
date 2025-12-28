# Руководство по реализации

## Фазы разработки проекта

Проект разделен на фазы для постепенной реализации и тестирования функциональности.

---

## Фаза 1: Базовый краулер (1-2 недели)

### Цель
Создать работающий краулер для одного источника (например, eBay Kleinanzeigen).

### Задачи

1. **Настройка окружения**
   - Python 3.11+ виртуальное окружение
   - Установка зависимостей: requests, beautifulsoup4, lxml
   - Настройка SQLite базы данных

2. **Реализация базового краулера**
   ```python
   # src/crawler/ebay_crawler.py
   class EbayCrawler:
       def __init__(self, config):
           self.config = config
           self.session = requests.Session()

       def fetch_page(self, url):
           """Получение HTML страницы"""
           pass

       def parse_listing(self, html):
           """Парсинг списка объявлений"""
           pass

       def parse_ad_detail(self, html):
           """Парсинг детальной страницы объявления"""
           pass

       def run(self):
           """Основной цикл краулера"""
           pass
   ```

3. **Схема базы данных**
   - Создание таблицы `ads`
   - Создание индексов
   - Миграции (Alembic или SQL скрипты)

4. **Тестирование**
   - Сбор 100-500 объявлений
   - Проверка корректности данных
   - Обработка ошибок

### Критерии завершения
- [ ] Краулер успешно собирает объявления из одного источника
- [ ] Данные сохраняются в БД
- [ ] Обрабатываются ошибки сети
- [ ] Логирование работы

---

## Фаза 2: Обработка данных (1 неделя)

### Цель
Очистка и нормализация собранных данных.

### Задачи

1. **Data Pipeline**
   ```python
   # src/database/pipeline.py
   class DataPipeline:
       def clean_text(self, text):
           """Очистка HTML и спецсимволов"""
           pass

       def normalize_location(self, location):
           """Стандартизация адреса"""
           pass

       def detect_duplicates(self, ad):
           """Обнаружение дубликатов"""
           pass
   ```

2. **Геокодирование (опционально)**
   - Интеграция с OpenStreetMap Nominatim
   - Извлечение координат из адресов

3. **Дедупликация**
   - Хеширование контента
   - Поиск похожих объявлений

### Критерии завершения
- [ ] Текст очищен от HTML и артефактов
- [ ] Местоположения стандартизированы
- [ ] Дубликаты отфильтрованы

---

## Фаза 3: Классификация (1-2 недели)

### Цель
Автоматическая категоризация объявлений.

### Задачи

1. **Подготовка обучающих данных**
   - Ручная разметка 1000-2000 объявлений
   - Создание набора категорий
   - Балансировка классов

2. **Обучение модели**
   ```python
   # src/classifier/train.py
   from sklearn.pipeline import Pipeline
   from sklearn.feature_extraction.text import TfidfVectorizer
   from sklearn.naive_bayes import MultinomialNB
   from sklearn.model_selection import cross_val_score

   # Загрузка данных
   X_train, y_train = load_training_data()

   # Создание пайплайна
   classifier = Pipeline([
       ('tfidf', TfidfVectorizer(
           max_features=5000,
           ngram_range=(1, 2),
           stop_words='german'  # или 'english'
       )),
       ('clf', MultinomialNB())
   ])

   # Обучение
   classifier.fit(X_train, y_train)

   # Оценка
   scores = cross_val_score(classifier, X_train, y_train, cv=5)
   print(f"Accuracy: {scores.mean():.2f} (+/- {scores.std():.2f})")

   # Сохранение модели
   import joblib
   joblib.dump(classifier, 'data/models/classifier.pkl')
   ```

3. **Интеграция в pipeline**
   - Автоматическая классификация новых объявлений
   - Сохранение категории в БД

4. **Извлечение характеристик**
   - Определение состояния (новое, б/у)
   - Извлечение брендов через regex

### Критерии завершения
- [ ] Модель обучена с точностью >80%
- [ ] Новые объявления автоматически категоризируются
- [ ] Характеристики извлекаются корректно

---

## Фаза 4: RSS/Atom генератор (1 неделя)

### Цель
Создание RSS лент для подписки на объявления.

### Задачи

1. **RSS Generator**
   ```python
   # src/notifier/rss_generator.py
   from feedgen.feed import FeedGenerator

   def generate_rss(ads, category=None, city=None):
       fg = FeedGenerator()
       fg.title(f'Бесплатные объявления - {category} - {city}')
       fg.link(href='https://yourserver.com', rel='alternate')
       fg.description('Бесплатные объявления о раздаче вещей')

       for ad in ads:
           fe = fg.add_entry()
           fe.title(ad['title'])
           fe.link(href=ad['url'])
           fe.description(ad['description'])
           fe.published(ad['posted_date'])

       return fg.rss_str(pretty=True)
   ```

2. **Статическая генерация**
   - Создание RSS файлов по категориям
   - Обновление по расписанию (cron)

3. **Структура URL**
   ```
   /rss/all.xml
   /rss/berlin/all.xml
   /rss/berlin/computers.xml
   /rss/berlin/kreuzberg/furniture.xml
   ```

4. **Web сервер (опционально)**
   - Flask/FastAPI для раздачи RSS
   - Динамическая генерация по запросу

### Критерии завершения
- [ ] RSS ленты генерируются корректно
- [ ] Файлы обновляются автоматически
- [ ] RSS доступны по HTTP

---

## Фаза 5: Email уведомления (1 неделя)

### Цель
Отправка email уведомлений подписчикам.

### Задачи

1. **Subscription Management**
   ```python
   # src/database/subscriptions.py
   class SubscriptionManager:
       def add_subscription(self, email, filters):
           """Добавить подписку"""
           pass

       def get_matching_ads(self, subscription):
           """Найти объявления по фильтрам"""
           pass

       def send_digest(self, subscription, ads):
           """Отправить дайджест"""
           pass
   ```

2. **Email Templates**
   - HTML шаблоны для писем
   - Форматирование объявлений

3. **SMTP интеграция**
   ```python
   # src/notifier/email_sender.py
   import smtplib
   from email.mime.text import MIMEText
   from email.mime.multipart import MIMEMultipart

   class EmailSender:
       def __init__(self, smtp_config):
           self.config = smtp_config

       def send_email(self, to, subject, html_content):
           msg = MIMEMultipart('alternative')
           msg['Subject'] = subject
           msg['From'] = self.config['from_email']
           msg['To'] = to

           html_part = MIMEText(html_content, 'html')
           msg.attach(html_part)

           with smtplib.SMTP(self.config['host'], self.config['port']) as server:
               server.starttls()
               server.login(self.config['username'], self.config['password'])
               server.send_message(msg)
   ```

4. **Планировщик**
   - Ежедневная отправка дайджестов
   - Немедленные уведомления (опционально)

### Критерии завершения
- [ ] Пользователи могут подписаться
- [ ] Email уведомления отправляются корректно
- [ ] Дубликаты не отправляются

---

## Фаза 6: Множественные источники (1-2 недели)

### Цель
Поддержка нескольких досок объявлений.

### Задачи

1. **Абстрактный класс краулера**
   ```python
   # src/crawler/base_crawler.py
   from abc import ABC, abstractmethod

   class BaseCrawler(ABC):
       @abstractmethod
       def fetch_listings(self):
           pass

       @abstractmethod
       def parse_ad(self, html):
           pass
   ```

2. **Реализация краулеров**
   - `EbayCrawler`
   - `CraigslistCrawler`
   - `OtherSourceCrawler`

3. **Конфигурация источников**
   ```yaml
   # config/sources.yaml
   sources:
     - name: ebay_kleinanzeigen
       enabled: true
       url: https://www.ebay-kleinanzeigen.de
       selectors:
         listing: "article.aditem"
         title: "h2.text-module-begin"
         location: "div.aditem-details"

     - name: craigslist
       enabled: true
       url: https://berlin.craigslist.org
       selectors:
         listing: "li.result-row"
         title: "a.result-title"
   ```

4. **Унификация данных**
   - Общий формат для всех источников
   - Маппинг категорий

### Критерии завершения
- [ ] Поддержка минимум 2 источников
- [ ] Данные из разных источников унифицированы
- [ ] Источники настраиваются через конфиг

---

## Фаза 7: Web API и интерфейс (2 недели, опционально)

### Цель
Создание web-интерфейса для просмотра и поиска объявлений.

### Задачи

1. **REST API**
   ```python
   # src/api/main.py
   from fastapi import FastAPI

   app = FastAPI()

   @app.get("/api/ads")
   def get_ads(category: str = None, city: str = None, limit: int = 50):
       """Получить список объявлений"""
       pass

   @app.get("/api/ads/{ad_id}")
   def get_ad_detail(ad_id: str):
       """Получить детали объявления"""
       pass

   @app.post("/api/subscriptions")
   def create_subscription(email: str, filters: dict):
       """Создать подписку"""
       pass
   ```

2. **Frontend (опционально)**
   - Простой HTML/CSS/JS интерфейс
   - Поиск и фильтрация
   - Управление подписками

3. **Полнотекстовый поиск**
   - SQLite FTS или PostgreSQL full-text search
   - Elasticsearch (для крупных инсталляций)

### Критерии завершения
- [ ] API работает и документирован (Swagger)
- [ ] Простой web-интерфейс доступен
- [ ] Поиск работает корректно

---

## Фаза 8: Оптимизация и production (1-2 недели)

### Цель
Подготовка к production развертыванию.

### Задачи

1. **Performance optimization**
   - Кеширование частых запросов
   - Индексы БД
   - Пагинация результатов

2. **Мониторинг и логирование**
   ```python
   # Structured logging
   import logging
   import json

   logger = logging.getLogger(__name__)
   logger.info(json.dumps({
       'event': 'crawler_completed',
       'source': 'ebay',
       'ads_collected': 150,
       'duration_seconds': 45
   }))
   ```

3. **Deployment**
   - Docker контейнеризация
   - Systemd сервисы для cron задач
   - Nginx для раздачи RSS

4. **Документация**
   - Installation guide
   - Configuration guide
   - Troubleshooting

### Критерии завершения
- [ ] Система работает стабильно
- [ ] Логи и метрики настроены
- [ ] Документация полная
- [ ] Развернуто в production

---

## Рекомендации по разработке

### Тестирование
- Unit тесты для критических компонентов
- Integration тесты для краулеров
- End-to-end тесты для RSS/email

### Git workflow
- Feature branches для каждой фазы
- Pull requests с code review
- Semantic versioning

### Code quality
- Type hints (Python 3.11+)
- Docstrings для всех публичных функций
- Linting: `black`, `flake8`, `mypy`

### Безопасность
- Валидация всех входных данных
- Rate limiting для краулеров
- Секреты в переменных окружения (не в коде!)

### Performance
- Асинхронный краулинг (aiohttp) для ускорения
- Batch insert в БД
- Connection pooling

---

## Минимальный MVP (Minimum Viable Product)

Для быстрого запуска можно ограничиться:
1. Базовый краулер для одного источника (Фаза 1)
2. Простая классификация (Фаза 3, только основные категории)
3. RSS генератор (Фаза 4)

**Время реализации MVP:** 2-3 недели

**Результат:** Работающая система, собирающая объявления и предоставляющая RSS ленты для подписки.
