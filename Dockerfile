FROM python:3.12.7-alpine
RUN apk --update add build-base bash jpeg-dev zlib-dev python3-dev

ENV PYTHONUNBUFFERED 1
ENV PYTHONDONTWRITEBYTECODE 1
ENV DJANGO_SETTINGS_MODULE demo.settings
ENV PYTHONPATH /app
ENV DEMO_DB_NAME /demo.sqlite3
RUN pip install django-extensions pillow freezegun

WORKDIR /app

COPY pyproject.toml /app
COPY src/picker /app/src/picker
COPY demo /app/demo
COPY tests /app/tests

RUN pip install -e /app
RUN django-admin migrate --no-input && \
    django-admin loaddata /app/demo/fixtures/picker.json && \
    django-admin import_picks /app/tests/nfl2024.json && \
    django-admin import_picks /app/tests/quidditch.json && \
    django-admin import_picks /app/tests/eng1.json

EXPOSE 8008
RUN echo Load at http://localhost:8008
CMD ["django-admin", "runserver", "0:8008"]
