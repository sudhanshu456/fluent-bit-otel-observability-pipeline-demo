from flask import Flask, jsonify
from opentelemetry.instrumentation.flask import FlaskInstrumentor
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import ConsoleMetricExporter, PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter

from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_INSTANCE_ID, SERVICE_NAME, SERVICE_VERSION, PROCESS_PID
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from importlib.metadata import version
import logging
import os
import random
import time
import sys
import socket

app = Flask(__name__)

# Set up logging
logging.basicConfig(stream=sys.stdout, level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

file_handler = logging.FileHandler('/var/log.log')
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
logger.addHandler(file_handler)

resource = Resource(attributes={SERVICE_NAME: 'demo-app', SERVICE_INSTANCE_ID: socket.gethostname(
), SERVICE_VERSION: '0.0.1', PROCESS_PID: os.getpid()})

# Set up tracing
trace.set_tracer_provider(TracerProvider(resource=resource))
otlp_span_exporter = OTLPSpanExporter(
    endpoint="http://fluentbit:3000/v1/traces", compression=False)
console_exporter = ConsoleSpanExporter()
span_processor = BatchSpanProcessor(otlp_span_exporter)
console_processor = BatchSpanProcessor(console_exporter)
trace.get_tracer_provider().add_span_processor(span_processor)
trace.get_tracer_provider().add_span_processor(console_processor)


metric_exporter = OTLPMetricExporter(
    endpoint="http://fluentbit:3000/v1/metrics")
console_exporter = ConsoleMetricExporter()
metric_reader = PeriodicExportingMetricReader(metric_exporter,export_interval_millis=2000)
# Export metrics to the console for testing
meter_provider = MeterProvider(
    resource=resource, metric_readers=[metric_reader])
metrics.set_meter_provider(meter_provider)
meter = metrics.get_meter(__name__)

requests_counter = meter.create_counter(name="requests_counter", description="number of requests", unit="1")
counter = meter.create_counter("counter")

otel_api_version = version('opentelemetry-api')
otel_sdk_version = version('opentelemetry-sdk')
otel_otlp_exporter_version = version('opentelemetry-exporter-otlp')

logger.info(
    f"API Version: {otel_api_version}\nSDK Version: {otel_sdk_version}\nOTLP Exporter Version: {otel_otlp_exporter_version}")


# Instrument Flask
FlaskInstrumentor().instrument_app(app)


@app.route('/')
def hello():
    return 'Hello, world!'

@app.route('/generate')
def generate():
    # Generate a random trace ID
    trace_id = '{:032x}'.format(random.getrandbits(128))
    logger.info(f'Generating trace {trace_id}')

    # Start a new span
    with trace.get_tracer(__name__).start_span('demo-span') as span:
        span.set_attribute('trace_id', trace_id)
        span.set_attribute('app.version', '1.0')

        # Generate a random log message
        log_message = f'Log message from trace {trace_id}'
        logger.info(log_message)

        # Generate a metric value
        counter_value = random.randint(0, 10)
        logger.info(f'Counter value from trace {trace_id}: {counter_value}')

        # request counter
        requests_counter.add(1)

        counter.add(counter_value)

        # Sleep for a random amount of time
        sleep_time = random.uniform(0.1, 1.0)
        time.sleep(sleep_time)

    return jsonify({'status': 'success'})

# add another endpoint to create hierarchical traces and so that we can see the trace tree in the UI, this endpoint will call the generate endpoint


@app.route('/generate-hierarchical')
def generate_hierarchical():
    with trace.get_tracer(__name__).start_span('parent-span') as span:
        span.set_attribute('app.version', '1.0')
        # add some delay to make the trace tree more interesting
        time.sleep(0.5)
        # start another span
        with trace.get_tracer(__name__).start_span('child-span') as child_span:
            time.sleep(0.5)
            return generate()


@app.route('/health')
def health():
    return jsonify({'status': 'ok'})


@app.route('/version')
def version():
    return jsonify({'version': '1.0'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
