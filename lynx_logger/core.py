"""
Основной модуль LynxLogger
"""

import sys
import logging
import structlog
from logging.handlers import RotatingFileHandler
from typing import Optional, Any, List, Union

from .config import LogConfig, Level, Format
from .formatters import get_formatter
from .filters import LogFilter
from .context import ContextProcessor


class LynxLogger:
    """
    Основной класс логгера на базе structlog с расширенными возможностями
    
    Example:
        >>> from lynx_logger import LogConfig, LynxLogger, Level, Format
        >>> config = LogConfig(name="my_app", level=Level.DEBUG, format=Format.JSON)
        >>> logger = LynxLogger(config)
        >>> logger.info("Application started", version="1.0.0", port=8000)
    """
    
    def __init__(self, config: LogConfig):
        """
        Инициализация логгера
        
        Args:
            config: Конфигурация логгера
        """
        self.config = config
        self._logger: Optional[structlog.BoundLogger] = None
        self._setup_logging()
    
    def _setup_logging(self):
        """Настройка системы логирования"""
        self._logger_instance = logging.getLogger(self.config.name)
        self._logger_instance.setLevel(self.config.level.value)
        
        if self._logger_instance.hasHandlers():
            self._logger_instance.handlers.clear()
        
        shared_processors = self._get_shared_processors()
        
        if self.config.console.enabled:
            self._setup_console_handler(self._logger_instance, shared_processors)
        
        if self.config.file.enabled:
            self._setup_file_handler(self._logger_instance, shared_processors)
        
        self._setup_structlog(shared_processors)
        
        self._logger = structlog.get_logger(self.config.name)
        
        self._apply_filters()
        if self._logger:      
            self._logger.info("Logger initialized", 
                            name=self.config.name,
                            level=self.config.level.name,
                            format=self.config.format.value)
    
    def _get_shared_processors(self) -> List[Any]:
        """Получение общих процессоров для всех обработчиков"""
        processors = [
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
        ]
        
        if self.config.context.include_caller:
            processors.append(structlog.processors.CallsiteParameterAdder(
                parameters=[structlog.processors.CallsiteParameter.FUNC_NAME,
                           structlog.processors.CallsiteParameter.LINENO]))
        
        if self.config.context.include_thread:
            processors.append(ContextProcessor.add_thread_info)
        
        if self.config.context.include_process:
            processors.append(ContextProcessor.add_process_info)
        
        processors.extend(self.config.extra_processors)

        # NOTE: these shared processors are used ONLY as the ProcessorFormatter's
        # `foreign_pre_chain` (see get_formatter / _setup_console_handler), i.e.
        # the chain applied to *foreign* (stdlib logging) records. It must NOT
        # end with `wrap_for_formatter` — that processor belongs to the native
        # structlog pipeline (added in _setup_structlog) and, when placed in a
        # foreign_pre_chain, makes `remove_processors_meta` raise
        # `TypeError: 'tuple' object does not support item deletion`, breaking
        # every log record emitted through the stdlib `logging` API.

        return processors
    
    def _setup_console_handler(self, root_logger: logging.Logger, shared_processors: List[Any]):
        """Настройка консольного обработчика"""
        formatter = get_formatter(
            self.config.format,
            shared_processors,
            colors=self.config.console.colors,
            dev_mode=self.config.dev_mode
        )
        
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(self.config.level.value)
        handler.setFormatter(formatter)
        
        root_logger.addHandler(handler)
    
    def _setup_file_handler(self, root_logger: logging.Logger, shared_processors: List[Any]):
        """Настройка файлового обработчика"""
        if not self.config.log_file_path:
            return
        
        max_bytes = self._parse_size(self.config.file.max_size)
        
        handler = RotatingFileHandler(
            filename=self.config.log_file_path,
            maxBytes=max_bytes,
            backupCount=self.config.file.backup_count,
            encoding=self.config.file.encoding,
            delay=self.config.file.delay
        )
        
        file_format = Format.JSON if self.config.format == Format.CONSOLE else self.config.format
        
        formatter = get_formatter(
            file_format,
            shared_processors,
            colors=False,
            dev_mode=self.config.dev_mode
        )
        
        handler.setLevel(self.config.level.value)
        handler.setFormatter(formatter)
        
        root_logger.addHandler(handler)
    
    def _setup_structlog(self, shared_processors: List[Any]):
        """Настройка structlog"""
        structlog_processors = [
            structlog.stdlib.add_logger_name,
            structlog.stdlib.add_log_level,
            structlog.stdlib.PositionalArgumentsFormatter(),
        ]
        
        if self.config.timestamp_format == "iso":
            structlog_processors.append(structlog.processors.TimeStamper(fmt="iso"))
        elif self.config.timestamp_format == "unix":
            structlog_processors.append(structlog.processors.TimeStamper(fmt=None))
        
        structlog_processors.extend([
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
        ])
        
        if self.config.context.custom_fields:
            structlog_processors.append(
                lambda _, __, event_dict: {**self.config.context.custom_fields, **event_dict}
            )
        
        structlog_processors.append(structlog.stdlib.ProcessorFormatter.wrap_for_formatter)
        
        structlog.configure(
            processors=structlog_processors,
            context_class=dict,
            logger_factory=structlog.stdlib.LoggerFactory(),
            wrapper_class=structlog.stdlib.BoundLogger,
            cache_logger_on_first_use=True,
        )
    
    def _apply_filters(self):
        """Применение фильтров к логгеру"""
        if self.config.filters.min_level:
            filter_obj = LogFilter.level_filter(self.config.filters.min_level)
            for handler in self._logger_instance.handlers:
                handler.addFilter(filter_obj)
        
        if self.config.filters.exclude_loggers:
            filter_obj = LogFilter.exclude_loggers(self.config.filters.exclude_loggers)
            for handler in self._logger_instance.handlers:
                handler.addFilter(filter_obj)
        
        if self.config.filters.include_only:
            filter_obj = LogFilter.include_only(self.config.filters.include_only)
            for handler in self._logger_instance.handlers:
                handler.addFilter(filter_obj)
    
    def _parse_size(self, size_str: str) -> int:
        """Преобразование строкового размера в байты"""
        size_str = size_str.upper().strip()
        
        if size_str.endswith('KB'):
            return int(size_str[:-2]) * 1024
        elif size_str.endswith('MB'):
            return int(size_str[:-2]) * 1024 * 1024
        elif size_str.endswith('GB'):
            return int(size_str[:-2]) * 1024 * 1024 * 1024
        else:
            return int(size_str)
    
    def get_logger(self) -> Optional[structlog.BoundLogger]:
        """
        Получение экземпляра structlog логгера
        
        Returns:
            Настроенный structlog логгер
        """
        return self._logger
    
    def bind(self, **kwargs) -> structlog.BoundLogger:
        """
        Создание нового логгера с привязанным контекстом
        
        Args:
            **kwargs: Поля контекста для привязки
            
        Returns:
            Логгер с привязанным контекстом
            
        Example:
            >>> request_logger = logger.bind(request_id="123", user_id="456")
            >>> request_logger.info("Processing request")
        """
        if self._logger is None:
            raise RuntimeError("Logger is not initialized")
        return self._logger.bind(**kwargs)
    
    def with_context(self, **kwargs) -> structlog.BoundLogger:
        """Алиас для bind()"""
        return self.bind(**kwargs)
    

    def debug(self, message: str, **kwargs):
        """Логирование на уровне DEBUG"""
        if self._logger is None:
            raise RuntimeError("Logger is not initialized")
        return self._logger.debug(message, **kwargs)
    
    def info(self, message: str, **kwargs):
        """Логирование на уровне INFO"""
        if self._logger is None:
            raise RuntimeError("Logger is not initialized")
        return self._logger.info(message, **kwargs)
    
    def warning(self, message: str, **kwargs):
        """Логирование на уровне WARNING"""
        if self._logger is None:
            raise RuntimeError("Logger is not initialized")
        return self._logger.warning(message, **kwargs)
    
    def warn(self, message: str, **kwargs):
        """Алиас для warning()"""
        return self.warning(message, **kwargs)
    
    def error(self, message: str, **kwargs):
        """Логирование на уровне ERROR"""
        if self._logger is None:
            raise RuntimeError("Logger is not initialized")
        return self._logger.error(message, **kwargs)
    
    def critical(self, message: str, **kwargs):
        """Логирование на уровне CRITICAL"""
        if self._logger is None:
            raise RuntimeError("Logger is not initialized")
        return self._logger.critical(message, **kwargs)
    
    def exception(self, message: str, **kwargs):
        """Логирование исключения с трассировкой стека"""
        if self._logger is None:
            raise RuntimeError("Logger is not initialized")
        return self._logger.exception(message, **kwargs)
    
    def log(self, level: Union[int, Level], message: str, **kwargs):
        """Логирование с указанным уровнем"""
        if isinstance(level, Level):
            level = level.value
        if self._logger is None:
            raise RuntimeError("Logger is not initialized")
        return self._logger.log(level, message, **kwargs)
    


    def __enter__(self):
        """Вход в контекстный менеджер"""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Выход из контекстного менеджера"""
        if exc_type is not None:
            self.exception("Exception in logger context", 
                          exc_type=exc_type.__name__, 
                          exc_value=str(exc_val))
    
    
    def set_level(self, level: Union[str, Level]):
        """Изменение уровня логирования во время выполнения"""
        if isinstance(level, str):
            level = Level.from_string(level)
        
        self.config.level = level
        self._logger_instance.setLevel(level.value)
        
        for handler in self._logger_instance.handlers:
            handler.setLevel(level.value)
        
        self.info("Log level changed", new_level=level.name)
    
    def get_config(self) -> LogConfig:
        """Получение текущей конфигурации"""
        return self.config
    
    def reload_config(self, new_config: LogConfig):
        """Перезагрузка конфигурации"""
        self.config = new_config
        self._setup_logging()
        self.info("Logger configuration reloaded")

