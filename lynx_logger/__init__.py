"""
LynxLogger - Универсальная библиотека логирования на основе structlog

Предоставляет гибкую настройку логирования для любых Python проектов
с поддержкой различных форматов, фильтров и интеграций
"""

from .core import LynxLogger
from .config import LogConfig, Format, Level
from .formatters import ConsoleFormatter, JSONFormatter, KeyValueFormatter
from .filters import LogFilter, LevelFilter, SourceFilter, ContentFilter
from .context import ContextLogger, RequestContext
from .middleware import FastAPILoggingMiddleware, ASGILoggingMiddleware

__version__ = "1.0.3"
__all__ = [
    # Core
    "LynxLogger",
    "LogConfig",
    
    # Configuration
    "Format", 
    "Level",
    
    # Formatters
    "ConsoleFormatter",
    "JSONFormatter", 
    "KeyValueFormatter",
    
    # Filters
    "LogFilter",
    "LevelFilter",
    "SourceFilter", 
    "ContentFilter",
    
    # Context
    "ContextLogger",
    "RequestContext",
    
    # Middleware
    "FastAPILoggingMiddleware",
    "ASGILoggingMiddleware",
]


def setup_logger(
    name: str = "lynx",
    level: str = "INFO",
    format: str = "console",
    dev_mode: bool = False,
    log_to_console: bool = True,
    log_to_file: bool = False,
    logs_dir: str = "./logs",
    **kwargs
) -> LynxLogger:
    """
    Быстрая настройка логгера с базовыми параметрами
    
    Args:
        name: Имя логгера
        level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        format: Формат логов (console, json, keyvalue)
        dev_mode: Режим разработки
        log_to_console: Логировать в консоль
        log_to_file: Логировать в файл
        logs_dir: Директория для файлов логов
        **kwargs: Дополнительные параметры для LogConfig
    
    Returns:
        Настроенный экземпляр LynxLogger
    
    Example:
        >>> logger = setup_logger("my_app", level="DEBUG", format="json")
        >>> logger.info("Application started", version="1.0.0")
    """
    config = LogConfig(
        name=name,
        level=Level.from_string(level),
        format=Format.from_string(format),
        dev_mode=dev_mode,
        log_to_console=log_to_console,
        log_to_file=log_to_file,
        logs_dir=logs_dir,
        **kwargs
    )
    
    return LynxLogger(config) 