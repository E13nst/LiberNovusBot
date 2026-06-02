# stdlib
import logging
import os
import time
from typing import Tuple

# thirdparty
from dotenv import load_dotenv
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from prometheus_client import REGISTRY, Counter, Gauge, Histogram
from prometheus_client.openmetrics.exposition import CONTENT_TYPE_LATEST, generate_latest
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Match
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR
from starlette.types import ASGIApp

load_dotenv()

# project
from services.config.runtime_config import get_runtime_config

_runtime = get_runtime_config()

logger = logging.getLogger(__name__)

ENV_MODE = _runtime.env_mode
TRACEBACK_OUTPUT_ENABLED = _runtime.traceback_output_enabled

DATABASE_URL = _runtime.database_url
DATABASE_URL_PSYCOPG2 = _runtime.database_url_psycopg2

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6389))

ASYNC_ENGINE_POOL_SIZE = int(os.getenv("ASYNC_ENGINE_POOL_SIZE", 20))
ASYNC_ENGINE_MAX_OVERFLOW = int(os.getenv("ASYNC_ENGINE_MAX_OVERFLOW", 50))

BOT_LINK = os.getenv("BOT_LINK", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")

RABBITMQ = {
    "PROTOCOL": "amqp",
    "HOST": os.getenv("RABBITMQ_HOST", "localhost"),
    "PORT": os.getenv("RABBITMQ_PORT", 5672),
    "USER": os.getenv("RABBITMQ_USER", "guest"),
    "PASSWORD": os.getenv("RABBITMQ_PASSWORD", "guest"),
}

CELERY_BROKER_URL = (
    f"{RABBITMQ['PROTOCOL']}://{RABBITMQ['USER']}:{RABBITMQ['PASSWORD']}@{RABBITMQ['HOST']}:{RABBITMQ['PORT']}"
)

OTLP_GRPC_ENDPOINT = _runtime.otlp_grpc_endpoint
LLM_PROVIDER = _runtime.llm_provider
OPENAI_API_KEY = _runtime.openai_api_key or ""
OPENAI_BASE_URL = _runtime.openai_base_url
LOCAL_LLM_BASE_URL = _runtime.local_llm_base_url
DEFAULT_MODEL = _runtime.default_model
LLM_MAX_ATTEMPTS = _runtime.llm_max_attempts
OPENAI_TIMEOUT_SECONDS = _runtime.openai_timeout_seconds
ANALYSIS_RUNTIME_ENABLED = _runtime.runtime_enabled
ANALYSIS_WORKER_CONCURRENCY = _runtime.analysis_worker_concurrency
ANALYSIS_WORKER_BATCH_SIZE = _runtime.analysis_worker_batch_size
ANALYSIS_WORKER_POLL_INTERVAL = _runtime.analysis_worker_poll_interval
ANALYSIS_JOB_MAX_ATTEMPTS = _runtime.analysis_job_max_attempts
ANALYSIS_JOB_STALE_TIMEOUT_SECONDS = _runtime.analysis_job_stale_timeout_seconds

INFO = Gauge("fastapi_app_info", "FastAPI application information.", ["app_name"])
REQUESTS = Counter(
    "fastapi_requests_total", "Total count of requests by method and path.", ["method", "path", "app_name"]
)
RESPONSES = Counter(
    "fastapi_responses_total",
    "Total count of responses by method, path and status codes.",
    ["method", "path", "status_code", "app_name"],
)
REQUESTS_PROCESSING_TIME = Histogram(
    "fastapi_requests_duration_seconds",
    "Histogram of requests processing time by path (in seconds)",
    ["method", "path", "app_name"],
)
EXCEPTIONS = Counter(
    "fastapi_exceptions_total",
    "Total count of exceptions raised by path and exception type",
    ["method", "path", "exception_type", "app_name"],
)
REQUESTS_IN_PROGRESS = Gauge(
    "fastapi_requests_in_progress",
    "Gauge of requests by method and path currently being processed",
    ["method", "path", "app_name"],
)


class PrometheusMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: ASGIApp, app_name: str = "mini-app-api") -> None:
        super().__init__(app)
        self.app_name = app_name
        INFO.labels(app_name=self.app_name).inc()

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        method = request.method
        path, is_handled_path = self.get_path(request)

        if not is_handled_path:
            return await call_next(request)

        REQUESTS_IN_PROGRESS.labels(method=method, path=path, app_name=self.app_name).inc()
        REQUESTS.labels(method=method, path=path, app_name=self.app_name).inc()
        before_time = time.perf_counter()
        try:
            response = await call_next(request)
        except BaseException as e:
            status_code = HTTP_500_INTERNAL_SERVER_ERROR
            EXCEPTIONS.labels(method=method, path=path, exception_type=type(e).__name__, app_name=self.app_name).inc()
            raise e from None
        else:
            status_code = response.status_code
            after_time = time.perf_counter()
            span = trace.get_current_span()
            trace_id = trace.format_trace_id(span.get_span_context().trace_id)

            REQUESTS_PROCESSING_TIME.labels(method=method, path=path, app_name=self.app_name).observe(
                after_time - before_time, exemplar={"TraceID": trace_id}
            )
        finally:
            RESPONSES.labels(method=method, path=path, status_code=status_code, app_name=self.app_name).inc()
            REQUESTS_IN_PROGRESS.labels(method=method, path=path, app_name=self.app_name).dec()

        return response

    @staticmethod
    def get_path(request: Request) -> Tuple[str, bool]:
        for route in request.app.routes:
            match, _ = route.matches(request.scope)
            if match == Match.FULL:
                return route.path, True

        return request.url.path, False


def metrics(request: Request) -> Response:
    return Response(generate_latest(REGISTRY), headers={"Content-Type": CONTENT_TYPE_LATEST})


def setting_otlp(app: ASGIApp, app_name: str, endpoint: str, log_correlation: bool = True) -> None:
    resource = Resource.create(attributes={"service.name": app_name, "compose_service": app_name})

    tracer = TracerProvider(resource=resource)
    trace.set_tracer_provider(tracer)

    tracer.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))

    if log_correlation:
        LoggingInstrumentor().instrument(set_logging_format=True)

    FastAPIInstrumentor.instrument_app(app, tracer_provider=tracer)
