# Observability

Observability provides information needed to understand the behavior of a running system.

Three commonly used signals are logs, metrics, and traces. Logs provide detailed event information, metrics provide numerical measurements over time, and traces show how an individual request moves through multiple services.

## Logs

Logs record application events and can provide detailed context about failures, configuration changes, authentication events, and background operations.

Structured logging allows fields such as service name, request ID, operation name, and error type to be searched consistently.

## Metrics

Metrics provide numerical measurements over time.

Latency metrics can reveal slow requests even when requests continue to succeed. Error-rate metrics show whether failures are increasing.

Other useful metrics include request volume, database connection utilization, cache hit rate, queue depth, retry counts, and resource utilization.

## Tracing

Distributed tracing is especially useful when a request crosses multiple services because the total latency can be divided among individual operations.

A trace can show whether time was spent in the API gateway, authentication service, database, downstream service, or another dependency.

## Correlation

A correlation ID allows events associated with the same request to be connected across service boundaries.

Correlation identifiers can connect API gateway logs, application logs, queue events, and database operations during incident investigation.

## Security

Observability data should avoid exposing secrets, credentials, access tokens, passwords, or other sensitive values.

Logs and traces should contain enough information to diagnose failures without recording the actual secret values involved in the operation.

## Operational Diagnosis

A useful incident investigation combines several signals rather than relying on a single metric.

For example, an increase in API latency can be investigated alongside database latency, queue depth, error rate, cache behavior, and downstream service timing.
