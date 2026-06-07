# OpenTelemetry

> Native OpenTelemetry instrumentation for distributed tracing.

FastMCP includes native OpenTelemetry instrumentation. Traces are automatically generated for tool, prompt, resource, and resource template operations, providing visibility into server behavior, request handling, and provider delegation chains.

## Setup

Install the OpenTelemetry SDK and an exporter:

```bash
pip install opentelemetry-sdk opentelemetry-exporter-otlp
```

Configure via environment variables before starting your server:

```bash
export OTEL_SERVICE_NAME=my-fastmcp-server
export OTEL_EXPORTER_OTLP_ENDPOINT=http://localhost:4317
```

Or configure programmatically using standard OpenTelemetry SDK setup before importing FastMCP.

## Backends

- **Local debugging**: `ConsoleSpanExporter` or `otel-desktop-viewer` gives quick feedback with minimal setup
- **Production**: OTLP exporters to Logfire, Jaeger, Tempo, Datadog, or New Relic
- **Sampling**: Tune sampling in the OpenTelemetry SDK to reduce trace volume without removing FastMCP instrumentation

FastMCP does not add OpenTelemetry as a required dependency — install it alongside FastMCP when needed. [1]

## References

1. [FastMCP Telemetry](https://gofastmcp.com/servers/telemetry.md) (accessed 2026-05-23)
