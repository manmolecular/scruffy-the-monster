FROM python:3.7-alpine AS scruffy-the-monster-build

LABEL org.label-schema.name="Scruffy The Monster" \
      org.label-schema.description="Simple Application to Show Basics of Race Conditions" \
      org.label-schema.license="GPL-2.0"

COPY . /app/
RUN apk add --no-cache gcc musl-dev && pip install --no-cache-dir -r /app/requirements.txt

WORKDIR /app
ENV PYTHONPATH="/app"
EXPOSE 9000
ENTRYPOINT ["python3", "server.py"]
