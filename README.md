<div align="center">

  # 🐱 Lynx Logger

  **The all-in-one structured logging solution for modern Python applications.**
  
  *Built on top of `structlog`. Designed for FastAPI, Flask, Django, and production scripts.*

  [![PyPI Version](https://img.shields.io/pypi/v/lynx-logger?style=flat-square&color=blue)](https://pypi.org/project/lynx-logger/)
  [![Python Versions](https://img.shields.io/pypi/pyversions/lynx-logger?style=flat-square)](https://pypi.org/project/lynx-logger/)
  [![License](https://img.shields.io/pypi/l/lynx-logger?style=flat-square)](https://opensource.org/licenses/MIT)
  [![Downloads](https://static.pepy.tech/personalized-badge/lynx-logger?period=total&units=INTERNATIONAL_SYSTEM&left_color=BLACK&right_color=GREEN&left_text=downloads)](https://pepy.tech/projects/lynx-logger)

  [Features](#-features) • [Installation](#-installation) • [Quick Start](#-quick-start) • [Configuration](#-configuration) • [Integrations](#-integrations)

</div>

---

## 🚀 Features

**Lynx Logger** bridges the gap between simple `print` debugging and complex enterprise logging systems.

* ✨ **Zero-Config Start:** Get beautiful logs with a single line of code.
* 📦 **Structured & JSON:** Native JSON support for ELK Stack, Datadog, or Loki.
* 🔍 **Context-Aware:** Automatic tracing of `request_id`, `user_id`, and trace contexts across your app.
* 🛡 **Smart Filtering:** Built-in filters for PII (GDPR compliance), log levels, and sources.
* 📂 **File Rotation:** Robust file handling with size limits and backups out of the box.
* 🔌 **Framework Ready:** Middleware included for **FastAPI**, **Flask**, and **Django**.

---

## 📦 Installation

```bash
pip install lynx-logger
````

**Optional Dependencies:**

|**Extra**|**Use Case**|
|---|---|
|`lynx-logger[web]`|Optimized for web frameworks (FastAPI, Starlette, Flask, Django)|
|`lynx-logger[all]`|Installs all dependencies including dev tools|

---

## ⚡ Quick Start

### 1. Basic Usage (Development)

Perfect for local development with readable, colored output.

```python
from lynx_logger import setup_logger

logger = setup_logger("my_service")

logger.info("Service started", version="1.0.0")
logger.warning("Cache miss", key="user:123", latency_ms=45)
# Output: 2025-02-05 [INFO] my_service: Service started version=1.0.0
```

### 2. Production Setup (JSON)

Optimized for log aggregators.


```python
logger = setup_logger(
    name="payment_service",
    level="INFO", 
    format="json",          # Outputs strict JSON
    log_to_file=True,
    logs_dir="./logs"
)

logger.info("Transaction processed", amount=500, currency="USD", user_id=42)
# Output: {"timestamp": "...", "level": "info", "event": "Transaction processed", "amount": 500, ...}
```

---

## 🎨 Output Formats

|**Format**|**Example Output**|**Best For**|
|---|---|---|
|**Console**|`[INFO] app: Server started port=8000` (Colored)|Local Development|
|**JSON**|`{"ts": "...", "level": "info", "msg": "Server started"}`|Production / ELK|
|**Key-Value**|`level=info event='Server started' port=8000`|Legacy Systems|

---

## 🧠 Context Management

Stop passing `user_id` as an argument to every function. Lynx Logger handles context for you.

### Automatic Context (Context Manager)

```python
from lynx_logger import RequestContext

# Automatically injects request_id into every log within this block
with RequestContext(request_id="req_123", user_id="user_456"):
    logger.info("Querying database") 
    # Log includes: request_id="req_123" user_id="user_456"
```

### Context Binding


```python
# Create a logger instance bound to specific data
job_logger = logger.bind(job_id="job_999")

job_logger.info("Job started") 
job_logger.info("Job finished")
# Both logs will contain job_id="job_999"
```

---

## 🛡 Advanced Filtering

### Throttling (Rate Limiting)

Prevent log flooding when errors occur in a loop.

```python
from lynx_logger import ThrottleFilter

# Allow max 10 identical messages per minute
throttle = ThrottleFilter(max_repeats=10, time_window=60)
```

### Content Filtering (GDPR/Security)

Automatically mask or exclude sensitive data.

```python
from lynx_logger import ContentFilter, LogConfig, LynxLogger

config = LogConfig(
    name="app",
    filters=ContentFilter(
        exclude_patterns=["password", "secret_key", "auth_token"],
        case_sensitive=False
    )
)
logger = LynxLogger(config)
```

---

## ⚙️ Configuration

Lynx Logger follows the **12-Factor App** methodology and can be configured via Environment Variables.

|**Environment Variable**|**Default**|**Description**|
|---|---|---|
|`LOG_NAME`|`root`|Service name|
|`LOG_LEVEL`|`INFO`|Logging level (DEBUG, INFO, ERROR)|
|`LOG_FORMAT`|`console`|Output format: `console`, `json`, `keyvalue`|
|`LOG_TO_FILE`|`false`|Enable file logging|
|`LOG_DIR`|`./logs`|Directory for log files|

**Or via Python Dictionary:**

```python
config = LogConfig.from_dict({
    "name": "worker",
    "level": "DEBUG",
    "file": {
        "filename": "worker.log",
        "max_size": "50MB",
        "backup_count": 5
    }
})
```

---

## 🔌 Integrations

### FastAPI Middleware Example


```python
from fastapi import FastAPI, Request
from lynx_logger import setup_logger, RequestContext
import uuid

app = FastAPI()
logger = setup_logger("api", format="json")

@app.middleware("http")
async def log_middleware(request: Request, call_next):
    req_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    
    # Context is automatically cleared after the request finishes
    with RequestContext(request_id=req_id, path=request.url.path):
        logger.info("Request started")
        response = await call_next(request)
        logger.info("Request finished", status=response.status_code)
        return response
```

---

## 🤝 Contributing

Contributions are welcome!

1. Fork the repository.
    
2. Create your feature branch.
    
3. Commit your changes.
    
4. Open a Pull Request.
    

Please open an [Issue](https://github.com/FlacSy/lynx-logger/issues) for any bugs or feature requests.

## 📄 License

This project is licensed under the **MIT License**.

<div align="center">

<sub>Developed with ❤️ by <a href="https://github.com/FlacSy">FlacSy</a></sub>

</div>
