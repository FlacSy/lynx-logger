# LynxLogger Roadmap (2025-2026)

**Фокус:** стабильный API, высокая DX (developer experience), готовые интеграции и конкурентоспособность с `loguru` и `structlog`.

---

## Видение

LynxLogger = **удобный, быстрый и production-ready логгер для Python**

* Простота (`logging` → одна строчка замены).
* Производительность (`orjson` + async/batch writer).
* Интеграции (FastAPI, SQLAlchemy, Celery, Requests).
* Совместимость (работает с `logging`, `structlog`, OpenTelemetry).

---

## Версии и сроки

### **v1.1.0 - "Стабилизация" (Сентябрь 2025)**

**Фокус:** стабильный API, тесты, документация.

* [ ] Строгий API (6 точек входа: `setup_logger`, `LynxLogger`, `LogConfig`, `RequestContext`, `Filters`, `Formatters`).
* [ ] Type hints, docstrings, inline-комментарии.
* [ ] Полное покрытие тестами (95%+).
* [ ] Автоматический CI/CD (GitHub Actions).
* [ ] Документация (Sphinx + readthedocs).
* [ ] Benchmark против `logging`, `loguru`, `structlog`.

---

### **v1.2.0 - "Интеграции" (Октябрь-Ноябрь 2025)**

**Фокус:** реальная польза → готовые модули для популярных стеков.

* [ ] FastAPI/Django/Flask middleware (с trace\_id и user\_id).
* [ ] SQLAlchemy: лог запросов + execution time.
* [ ] Celery: лог задач (id, статус, ошибка).
* [ ] Requests/httpx: автоматический лог исходящих HTTP-запросов.
* [ ] Redis (команды и ошибки).
* [ ] Экспорт в Prometheus (счётчик логов, error rate).

---

### **v1.3.0 - "Производительность" (Декабрь 2025)**

**Фокус:** Rust-ядро, асинхронность и минимальные накладные расходы.

- [ ] **Rust core (`lynx_core`)**:
  - высокопроизводительная JSON-сериализация (`serde_json` / `simd-json`);
  - batch writer (stdout, файл, TCP/UDP);
  - ротация файлов на уровне Rust (без GIL).
- [ ] **PyO3 биндинги** для интеграции с Python API.
- [ ] **AsyncLogger** (async/await в Python) → под капотом кидает события в Rust-очередь.
- [ ] **Batch logging**: буферизация логов в Rust (очередь + flush по таймеру/размеру).
- [ ] **Zero-allocation API**: минимизация копирований строк (использование `&'static str` и `Cow<str>`).
- [ ] **Lazy init**: форматтеры и фильтры инициализируются только при первом вызове.
- [ ] **Бенчмарки**:
  - LynxLogger (Python-только vs Rust-core)
  - сравнение с `structlog` и `loguru`
  - цели:
    - ≥2× быстрее `structlog`
    - близко к `loguru` по latency

---

**Последнее обновление:** 26 августа 2025  
**Следующий review:** 1 ноября 2025  
**Версия roadmap:** 2.0 
