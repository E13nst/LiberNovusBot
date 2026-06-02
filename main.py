# stdlib
import asyncio
import logging

# thirdparty
import uvicorn
from fastapi import APIRouter, FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.openapi.utils import get_openapi
from starlette.responses import RedirectResponse

# project
import settings
from db.db_setup import async_session
from routers.admin import admin_router
from routers.analysis_jobs import analysis_jobs_router
from routers.dreams import dreams_router
from routers.players import players_router
from routers.session_analysis import session_analysis_router
from routers.sessions import sessions_router
from routers.telegram_webhook import telegram_webhook_router
from services.config.startup_validation import run_startup_validation, should_start_runtime_worker
from services.runtime.analysis_runtime_worker import AnalysisRuntimeWorker
from settings import PrometheusMiddleware, metrics, setting_otlp
from utils.helpers import (
    CustomHTTPException,
    custom_exception_handler,
    general_exception_handler,
    validation_exception_handler,
)

root_router = APIRouter(prefix="/api/v1")


app = FastAPI(title="Mini-App-API", version="0.0.1")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

root_router.include_router(players_router)

app.include_router(telegram_webhook_router, prefix="/telegram")
app.include_router(dreams_router, prefix="/dreams")
app.include_router(sessions_router, prefix="/sessions")
app.include_router(session_analysis_router, prefix="/sessions")
app.include_router(analysis_jobs_router)
app.include_router(admin_router)
app.include_router(root_router)


@app.get("/")
async def root():
    return RedirectResponse(url="/docs")


def validate_startup() -> None:
    """CLI/prod-check entrypoint: pure config validation without starting the app."""
    from services.config.startup_validation import validate_startup_sync

    validate_startup_sync()


@app.on_event("startup")
async def start_runtime_worker():
    await run_startup_validation()
    if not should_start_runtime_worker():
        return

    worker = AnalysisRuntimeWorker(
        session_factory=async_session,
        worker_id="fastapi-runtime-worker",
        batch_size=settings.ANALYSIS_WORKER_BATCH_SIZE,
        max_concurrency=settings.ANALYSIS_WORKER_CONCURRENCY,
        poll_interval_seconds=settings.ANALYSIS_WORKER_POLL_INTERVAL,
    )
    app.state.analysis_runtime_worker = worker
    app.state.analysis_runtime_worker_task = asyncio.create_task(worker.run_forever())


@app.on_event("shutdown")
async def stop_runtime_worker():
    worker = getattr(app.state, "analysis_runtime_worker", None)
    task = getattr(app.state, "analysis_runtime_worker_task", None)
    if worker is None or task is None:
        return

    await worker.stop()
    await task


class EndpointFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return record.getMessage().find("GET /metrics") == -1


class Non200Filter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        return not record.getMessage().endswith("200")


logging.getLogger("uvicorn.access").addFilter(EndpointFilter())
logging.getLogger("uvicorn.access").addFilter(Non200Filter())

app.add_middleware(PrometheusMiddleware, app_name="mini-app-api")
app.add_route("/metrics", metrics)

setting_otlp(app, "mini-app-api", settings.OTLP_GRPC_ENDPOINT)

app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(CustomHTTPException, custom_exception_handler)
app.add_exception_handler(Exception, general_exception_handler)


def openapi_specs():
    if app.openapi_schema:
        return app.openapi_schema
    openapi_schema = get_openapi(
        title="Mini App",
        version="1.0.0",
        description="Mini App API Open-API Specification",
        routes=app.routes,
    )
    app.openapi_schema = openapi_schema
    return app.openapi_schema


app.openapi = openapi_specs

if __name__ == "__main__":
    log_config = uvicorn.config.LOGGING_CONFIG
    log_config["formatters"]["access"]["fmt"] = (
        "%(asctime)s %(levelname)s [%(name)s] [%(filename)s:%(lineno)d] "
        "[trace_id=%(otelTraceID)s span_id=%(otelSpanID)s resource.service.name=%(otelServiceName)s] - %(message)s"
    )
    uvicorn.run(app, host="0.0.0.0", port=8000, log_config=log_config)
