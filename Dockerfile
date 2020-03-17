FROM python:3.8-alpine AS scruffy-the-monster-build

LABEL org.label-schema.name="Scruffy The Monster" \
      org.label-schema.description="Simple Application to Show Basics of Race Conditions" \
      org.label-schema.license="GPL-2.0"

COPY . /app/
WORKDIR /app
RUN apk add --no-cache gcc musl-dev libressl-dev libffi-dev curl && \
    curl -sSL https://raw.githubusercontent.com/sdispater/poetry/master/get-poetry.py > get-poetry.py && \
    python get-poetry.py -y --version 1.0.5 && \
    source ~/.poetry/env && \
    poetry config virtualenvs.create false && \
    poetry install --no-dev --no-interaction && \
    python get-poetry.py --uninstall -y && \
    rm -rf ~/.config/pypoetry && \
    apk del gcc libressl-dev musl-dev libffi-dev curl

ENV PYTHONPATH="/app"
EXPOSE 9000
ENTRYPOINT ["python3", "server.py"]
