import os

from celery import Celery
from dotenv import load_dotenv

_ = load_dotenv()

BROKER_REGISTRY = {
    "rabbitmq": "RABBITMQ_BROKER_URL",
    "redis": "REDIS_BROKER_URL",
}

CELERY_BROKER = os.environ.get("CELERY_BROKER", None)
if CELERY_BROKER is None:
    raise ValueError(
        "You must set the CELERY_BROKER environment variable. ",
        f"Supported brokers: {list(BROKER_REGISTRY.keys())}",
    )

if CELERY_BROKER not in BROKER_REGISTRY:
    raise ValueError(
        f"Unsupported broker: {CELERY_BROKER}. ",
        f"Supported brokers: {list(BROKER_REGISTRY.keys())}",
    )

broker_url_env_var = BROKER_REGISTRY[CELERY_BROKER]
BROKER_URL = os.environ.get(broker_url_env_var, None)

if BROKER_URL is None:
    raise ValueError(
        f"The {broker_url_env_var} environment variable is not set.",
    )


app = Celery("kul_ocr", broker=BROKER_URL)

app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_default_retry_delay=60,
    task_max_retries=3,
)
