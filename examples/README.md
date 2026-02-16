# LynxLogger Usage Examples

This directory contains examples of using LynxLogger in various scenarios.

## Available Examples

### 1. [simple_app.py](simple_app.py) - Simple Example
Basic example of using LynxLogger without a web framework.

**Features:**
- Creating a logger with `setup_logger`
- Logging with context (`RequestContext`)
- Exception handling
- Logging to file and console

**Run:**
```bash
python3 simple_app.py
```

### 2. [formats_demo.py](formats_demo.py) - Format Demonstration
Demonstrates different logging formats.

**Features:**
- JSON format
- Key-Value format
- Console format (with colors)
- Plain text format
- Logging to file
- Mixed logging (console + file)

**Run:**
```bash
python3 formats_demo.py
```

### 3. [fastapi_app.py](fastapi_app.py) - FastAPI Application
Example of integration with FastAPI.

**Features:**
- FastAPI application with middleware
- Automatic HTTP request logging
- Contextual information (request_id, trace_id)
- Request processing time logging

**Run:**
```bash
# Requires FastAPI and uvicorn
pip install fastapi uvicorn
python3 fastapi_app.py
```

### 4. [flask_app.py](flask_app.py) - Flask Application
Example of integration with Flask.

**Features:**
- Flask application with middleware
- Automatic request logging
- Request parameter logging

**Run:**
```bash
# Requires Flask
pip install flask
python3 flask_app.py
```

### 5. [django_app.py](django_app.py) - Django Application
Example of integration with Django.

**Features:**
- Django application with middleware
- Automatic request logging
- Request data logging
- Using `LynxLogger` directly

**Run:**
```bash
# Requires Django
pip install django
python3 django_app.py
```

## Log Structure

All examples create logs in the `./logs/` directory:

- `app.log` - main log file
- `fastapi_app.log` - FastAPI application logs
- `flask_app.log` - Flask application logs
- `django_app.log` - Django application logs

## Log Formats

LynxLogger supports the following formats:

1. **JSON** - structured JSON format
2. **Key-Value** - key=value format
3. **Console** - colored console format
4. **Plain** - plain text format

## Contextual Logging

Examples demonstrate using `RequestContext` to automatically add contextual information:

```python
with RequestContext(request_id="req_123", user_id="user_456"):
    logger.info("Processing request")
```

## Bound Loggers

Examples show how to create bound loggers with additional fields:

```python
api_logger = logger.bind(component="api", version="v1")
user_logger = api_logger.bind(user_id="user_789")
```

## Logger Creation

Examples demonstrate two ways to create a logger:

### 1. Via `setup_logger` (simple approach)
```python
from lynx_logger import setup_logger

logger = setup_logger(
    name="my_app",
    level="INFO",
    format="json",
    log_to_console=True,
    log_to_file=True,
    logs_dir="./logs"
)
```

### 2. Via `LynxLogger` directly (advanced approach)
```python
from lynx_logger import LynxLogger, Level, Format
from lynx_logger.config import LogConfig, FileConfig

logger = LynxLogger(
    LogConfig(
        name="my_app",
        level=Level.INFO,
        format=Format.JSON,
        log_to_console=True,
        file=FileConfig(
            enabled=True,
            filename="my_app.log",
            max_size="10MB",
            backup_count=5
        )
    )
)
```

## Running Examples

To run examples without web frameworks:

```bash
python3 simple_app.py
python3 formats_demo.py
```

Running examples with web frameworks requires installing the corresponding dependencies.
