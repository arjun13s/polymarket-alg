FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml README.md ./
COPY controller ./controller
COPY environment ./environment
COPY src ./src
COPY examples ./examples
COPY tests ./tests

RUN pip install --no-cache-dir .

ENTRYPOINT ["python", "-m", "controller"]
