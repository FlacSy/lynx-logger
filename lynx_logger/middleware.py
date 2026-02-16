"""
Middleware для интеграции с веб-фреймворками
"""

import time
import uuid
from typing import Optional, List, Set
import structlog

from .context import RequestContext, request_id_ctx, user_id_ctx, trace_id_ctx

# Заголовки, которые маскируются в логах (без утечки токенов, паролей)
DEFAULT_SENSITIVE_HEADERS: Set[str] = {
    "authorization",
    "cookie",
    "set-cookie",
    "x-api-key",
    "x-auth-token",
    "proxy-authorization",
}

# Ключи в form/query/POST, которые маскируются
DEFAULT_SENSITIVE_KEYS: Set[str] = {
    "password",
    "passwd",
    "token",
    "secret",
    "api_key",
    "csrf_token",
    "session",
}


def _sanitize_headers(headers: dict, sensitive: Set[str]) -> dict:
    """Маскирует чувствительные заголовки значением ***."""
    return {
        k: ("***" if k.lower() in sensitive else v)
        for k, v in headers.items()
    }


def _sanitize_dict(data: dict, sensitive_keys: Set[str]) -> dict:
    """Маскирует чувствительные ключи в словаре (form, query, POST)."""
    if not data:
        return data
    return {
        k: ("***" if k.lower() in sensitive_keys else v)
        for k, v in data.items()
    }


def _scope_headers_to_dict(scope: dict) -> dict:
    """Преобразует ASGI scope['headers'] в dict."""
    return {
        h[0].decode("latin-1"): h[1].decode("latin-1")
        for h in scope.get("headers", [])
    }


class FastAPILoggingMiddleware:
    """Middleware для FastAPI с автоматическим логированием запросов"""
    
    def __init__(
        self,
        logger: structlog.BoundLogger,
        log_requests: bool = True,
        log_responses: bool = True,
        exclude_paths: List[str] | None = None,
        include_request_body: bool = False,
        include_response_body: bool = False,
        max_body_size: int = 1024,
        sensitive_headers: List[str] | None = None,
    ):
        """
        Args:
            logger: Логгер для записи
            log_requests: Логировать входящие запросы
            log_responses: Логировать исходящие ответы
            exclude_paths: Пути для исключения из логирования
            include_request_body: Включать тело запроса в логи
            include_response_body: Включать тело ответа в логи
            max_body_size: Максимальный размер тела для логирования
            sensitive_headers: Заголовки, маскируемые как *** (по умолчанию:
                authorization, cookie, set-cookie, x-api-key, x-auth-token, proxy-authorization)
        """
        self.logger = logger
        self.log_requests = log_requests
        self.log_responses = log_responses
        self.exclude_paths = exclude_paths or ["/health", "/metrics", "/favicon.ico"]
        self.include_request_body = include_request_body
        self.include_response_body = include_response_body
        self.max_body_size = max_body_size
        self._sensitive_headers = (
            set(h.lower() for h in sensitive_headers)
            if sensitive_headers
            else DEFAULT_SENSITIVE_HEADERS
        )
    
    def __call__(self, app):
        """Создает middleware для FastAPI"""
        async def middleware(request, call_next):
            """Обработка запроса"""
            request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
            trace_id = request.headers.get("X-Trace-ID") or str(uuid.uuid4())
            user_id = request.headers.get("X-User-ID")
            
            if request.url.path in self.exclude_paths:
                response = await call_next(request)
                return response
            
            with RequestContext(request_id=request_id, user_id=user_id, trace_id=trace_id):
                start_time = time.time()

                request_logger = self.logger.bind(
                    request_id=request_id,
                    trace_id=trace_id,
                    user_id=user_id,
                    method=request.method,
                    path=request.url.path,
                    query_params=str(request.query_params) if request.query_params else None,
                    user_agent=request.headers.get("User-Agent"),
                    client_ip=self._get_client_ip(request)
                )
                
                if self.log_requests:
                    log_data = {
                        "method": request.method,
                        "path": request.url.path,
                        "query_params": dict(request.query_params),
                        "headers": _sanitize_headers(
                            dict(request.headers), self._sensitive_headers
                        ),
                    }

                    if self.include_request_body:
                        body = await self._get_request_body(request)
                        if body:
                            log_data["request_body"] = body
                    
                    request_logger.info("HTTP request", **log_data)
                
                try:
                    response = await call_next(request)
                    
                    process_time = time.time() - start_time
                    
                    if self.log_responses:
                        log_data = {
                            "status_code": response.status_code,
                            "process_time": round(process_time, 4),
                            "response_headers": _sanitize_headers(
                                dict(response.headers), self._sensitive_headers
                            ),
                        }
                        
                        if self.include_response_body:
                            body = await self._get_response_body(response)
                            if body:
                                log_data["response_body"] = body
                        
                        if response.status_code >= 500:
                            request_logger.error("HTTP response", **log_data)
                        elif response.status_code >= 400:
                            request_logger.warning("HTTP response", **log_data)
                        else:
                            request_logger.info("HTTP response", **log_data)
                    
                    response.headers["X-Request-ID"] = request_id
                    response.headers["X-Trace-ID"] = trace_id
                    response.headers["X-Process-Time"] = str(round(process_time, 4))
                    
                    return response
                    
                except Exception as exc:
                    process_time = time.time() - start_time
                    request_logger.exception(
                        "Request failed",
                        exception_type=type(exc).__name__,
                        exception_message=str(exc),
                        process_time=round(process_time, 4)
                    )
                    raise
        
        return middleware
    
    def _get_client_ip(self, request) -> str:
        """Получает IP клиента"""
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()
        
        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip
        
        return getattr(request.client, "host", "unknown")
    
    async def _get_request_body(self, request) -> Optional[str]:
        """Получает тело запроса для логирования"""
        try:
            body = await request.body()
            if len(body) <= self.max_body_size:
                return body.decode("utf-8", errors="ignore")
            else:
                return f"[Body too large: {len(body)} bytes]"
        except Exception:
            return "[Unable to read body]"
    
    async def _get_response_body(self, response) -> Optional[str]:
        """Получает тело ответа для логирования"""
        # Это сложно реализовать без изменения response
        # Обычно не рекомендуется логировать тело ответа
        return None


class ASGILoggingMiddleware:
    """ASGI middleware для логирования"""

    def __init__(
        self,
        app,
        logger: structlog.BoundLogger,
        log_level: str = "INFO",
        log_headers: bool = True,
        sensitive_headers: List[str] | None = None,
    ):
        """
        Args:
            app: ASGI приложение
            logger: Логгер
            log_level: Уровень логирования
            log_headers: Логировать заголовки (с маскировкой чувствительных)
            sensitive_headers: Заголовки для маскировки (по умолчанию — DEFAULT_SENSITIVE_HEADERS)
        """
        self.app = app
        self.logger = logger
        self.log_level = log_level
        self.log_headers = log_headers
        self._sensitive_headers = (
            set(h.lower() for h in sensitive_headers)
            if sensitive_headers
            else DEFAULT_SENSITIVE_HEADERS
        )

    async def __call__(self, scope, receive, send):
        """ASGI call"""
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request_id = str(uuid.uuid4())

        method = scope["method"]
        path = scope["path"]
        query_string = scope.get("query_string", b"").decode()

        start_time = time.time()

        log_kwargs = dict(
            request_id=request_id,
            method=method,
            path=path,
            query_string=query_string or None,
        )
        if self.log_headers:
            headers = _scope_headers_to_dict(scope)
            log_kwargs["headers"] = _sanitize_headers(
                headers, self._sensitive_headers
            )

        request_logger = self.logger.bind(**log_kwargs)

        request_logger.info("ASGI request started")
        
        async def send_with_logging(message):
            """Wrapper для send с логированием"""
            if message["type"] == "http.response.start":
                status_code = message["status"]
                process_time = time.time() - start_time
                
                request_logger.info(
                    "ASGI request completed",
                    status_code=status_code,
                    process_time=round(process_time, 4)
                )
            
            await send(message)
        
        try:
            await self.app(scope, receive, send_with_logging)
        except Exception as exc:
            process_time = time.time() - start_time
            request_logger.exception(
                "ASGI request failed",
                exception_type=type(exc).__name__,
                exception_message=str(exc),
                process_time=round(process_time, 4)
            )
            raise


class FlaskLoggingMiddleware:
    """Middleware для Flask"""

    def __init__(
        self,
        app,
        logger: structlog.BoundLogger,
        log_requests: bool = True,
        log_responses: bool = True,
        log_headers: bool = False,
        sensitive_headers: List[str] | None = None,
        sensitive_keys: List[str] | None = None,
    ):
        """
        Args:
            app: Flask приложение
            logger: Логгер
            log_requests: Логировать запросы
            log_responses: Логировать ответы
            log_headers: Логировать заголовки (с маскировкой)
            sensitive_headers: Заголовки для маскировки
            sensitive_keys: Ключи в args/form для маскировки (password, token и др.)
        """
        self.app = app
        self.logger = logger
        self.log_requests = log_requests
        self.log_responses = log_responses
        self.log_headers = log_headers
        self._sensitive_headers = (
            set(h.lower() for h in sensitive_headers)
            if sensitive_headers
            else DEFAULT_SENSITIVE_HEADERS
        )
        self._sensitive_keys = (
            set(k.lower() for k in sensitive_keys)
            if sensitive_keys
            else DEFAULT_SENSITIVE_KEYS
        )

        app.before_request(self._before_request)
        app.after_request(self._after_request)
        app.teardown_request(self._teardown_request)

    def _before_request(self):
        """Обработчик перед запросом"""
        from flask import request, g

        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        g.request_id = request_id
        g.start_time = time.time()

        if self.log_requests:
            log_data = dict(
                request_id=request_id,
                method=request.method,
                path=request.path,
                remote_addr=request.remote_addr,
                args=_sanitize_dict(dict(request.args), self._sensitive_keys),
                form=(
                    _sanitize_dict(dict(request.form), self._sensitive_keys)
                    if request.form
                    else None
                ),
            )
            if self.log_headers:
                log_data["headers"] = _sanitize_headers(
                    dict(request.headers), self._sensitive_headers
                )

            request_logger = self.logger.bind(**log_data)

            request_logger.info("Flask request started")

            g.request_logger = request_logger
    
    def _after_request(self, response):
        """Обработчик после запроса"""
        from flask import g

        if self.log_responses and hasattr(g, "request_logger"):
            process_time = time.time() - g.start_time
            
            g.request_logger.info(
                "Flask request completed",
                status_code=response.status_code,
                process_time=round(process_time, 4)
            )
        
        if hasattr(g, 'request_id'):
            response.headers["X-Request-ID"] = g.request_id
        
        return response
    
    def _teardown_request(self, exception):
        """Обработчик завершения запроса"""
        from flask import g

        if exception and hasattr(g, "request_logger"):
            process_time = time.time() - g.start_time
            
            g.request_logger.exception(
                "Flask request failed",
                exception_type=type(exception).__name__,
                exception_message=str(exception),
                process_time=round(process_time, 4)
            )


class DjangoLoggingMiddleware:
    """Middleware для Django. Маскирует password, token и др. в query_params/post_params."""

    def __init__(self, get_response):
        """
        Args:
            get_response: Django get_response функция
        """
        self.get_response = get_response
        self.logger = structlog.get_logger("django")
        self._sensitive_keys = DEFAULT_SENSITIVE_KEYS

    def __call__(self, request):
        """Обработка запроса"""
        request_id = str(uuid.uuid4())
        request.request_id = request_id

        start_time = time.time()

        query_params = _sanitize_dict(dict(request.GET), self._sensitive_keys)
        post_params = (
            _sanitize_dict(dict(request.POST), self._sensitive_keys)
            if request.POST
            else None
        )

        request_logger = self.logger.bind(
            request_id=request_id,
            method=request.method,
            path=request.path,
            user=str(request.user) if hasattr(request, "user") else None,
        )

        request_logger.info(
            "Django request started",
            query_params=query_params,
            post_params=post_params,
        )
        
        try:
            response = self.get_response(request)
            
            process_time = time.time() - start_time
            request_logger.info(
                "Django request completed",
                status_code=response.status_code,
                process_time=round(process_time, 4)
            )
            
            response["X-Request-ID"] = request_id
            
            return response
            
        except Exception as exc:
            process_time = time.time() - start_time
            request_logger.exception(
                "Django request failed",
                exception_type=type(exc).__name__,
                exception_message=str(exc),
                process_time=round(process_time, 4)
            )
            raise 