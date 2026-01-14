


rabbitmq-add-vhost:
    curl -s -X PUT -u guest:guest -H "Content-Type: application/json" \
        -d '{"description":"OCR Jobs"}' \
        http://localhost:15672/api/vhosts/dev.jobs
    curl -s -X PUT -u guest:guest -H "Content-Type: application/json" \
        -d '{"configure":".*","write":".*","read":".*"}' \
        "http://localhost:15672/api/permissions/dev.jobs/guest"


run-celery-app:
    uv run celery -A kul_ocr.entrypoints.celery_app worker --loglevel=info
