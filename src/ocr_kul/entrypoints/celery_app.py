from celery import Celery

app = Celery("ocr_kul", broker="amqp://guest@localhost")
