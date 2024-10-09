import http
import logging

from starlette.requests import Request
from starlette.types import ASGIApp, Receive, Scope, Send


class LoggerMiddleware:
    def __init__(self, app: ASGIApp, logger: logging.Logger) -> None:
        self.app = app
        self.logger = logger

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        request = Request(scope, receive)
        request_client = (
            {"host": request.client.host, "port": request.client.port}
            if request.client
            else {}
        )
        http_version = scope.get("http_version", "")
        request_info = {
            "client": request_client,
            "headers": dict(request.headers),
            "http_version": http_version,
            "method": request.method,
            "path_params": request.path_params,
            "query_params": dict(request.query_params),
            "url": {
                "path": request.url.path,
                "port": request.url.port,
                "scheme": request.url.scheme,
            },
        }
        request_line = f'{request_client.get("host", "unknown")}:{request_client.get("port", "unknown")} - "{request.method} {request.url} HTTP/{http_version}"'
        self.logger.info(request_line, extra=request_info)

        status_code: str
        body: bytes

        async def log_response(request_line: str) -> None:
            nonlocal status_code
            nonlocal body

            try:
                status_phrase = http.HTTPStatus(status_code).phrase
            except ValueError:
                status_phrase = ""
            status_and_phrase = f"{status_code} {status_phrase}"

            response_info = {
                "body": body,
                "status_code": status_code,
            }

            self.logger.info(f"{request_line} {status_and_phrase}", extra=response_info)

        async def send_wrapper(message):
            nonlocal status_code
            nonlocal body

            if message["type"] == "http.response.start":
                status_code = message["status"]
            elif message["type"] == "http.response.body":
                if not hasattr(self, "body"):
                    body = b""
                body += message.get("body", b"")
                if not message.get("more_body", False):
                    await log_response(request_line)
            await send(message)

        await self.app(scope, receive, send_wrapper)
