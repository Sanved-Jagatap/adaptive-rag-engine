# Structured Logging

Structured logging records application events using fields that can be searched and analyzed consistently.

## Log Fields

A structured log entry can include a timestamp, log level, service name, request ID, operation name, and error information.

Consistent field names make it easier to aggregate events across multiple application instances.

Request IDs and correlation identifiers are particularly useful when debugging distributed systems.

## Log Levels

Log levels commonly distinguish debug information, normal informational events, warnings, and errors.

Debug-level logging is generally more verbose and is useful during development or troubleshooting.

Informational logs can describe normal lifecycle events. Warning logs can identify unusual conditions that do not necessarily indicate a failure. Error logs should describe failures that require investigation.

## Sensitive Data

Production logs should avoid recording passwords, authentication tokens, secret keys, or complete sensitive payloads.

Logging an access token can create a security problem because log storage often has a longer retention period and broader access than the original application request.

Sensitive identifiers should be masked or omitted when they are not required for diagnosis.

## Distributed Troubleshooting

Correlation identifiers are particularly useful when debugging distributed systems.

A request ID can connect an incoming API request with database calls, queue operations, downstream service requests, and trace spans.

This allows an operator to reconstruct the path of a request without searching independently through unrelated application instances.

## Log Volume

Excessive debug logging can increase storage costs and make important events harder to find.

Logging should therefore balance diagnostic detail with storage, processing, and privacy requirements.

Logs should contain enough context to explain an event without requiring operators to inspect application memory or reproduce the request manually.
