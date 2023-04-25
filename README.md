# Open-telemetry observability pipeline using Fluent Bit

This repository contains a sample configuration for Fluent Bit that can be used to send logs to [OpenTelemetry Collector] and metrics to [OpenTelemetry Collector] or [Prometheus].

## Prerequisites

- [Docker]
- [Docker Compose]

## How to run

```bash
docker-compose up --build
```

## How to generate traces and metrics

```bash
curl -X GET http://localhost:5000/generate
```

It will generate traces and metrics.

## Generate Hierarchical Span

```bash
curl -X GET http://localhost:5000/generate-hierarchical
    ```
