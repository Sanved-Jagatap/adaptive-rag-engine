# API Gateway

The API gateway provides a common entry point for requests entering backend services. It can centralize controls that would otherwise need to be implemented separately by many services.

## Routing

Routing rules determine which backend service receives a request. A route can be selected using the request path, HTTP method, host, or other request attributes.

For example, requests associated with one API path can be forwarded to an authentication service while another path is forwarded to a payment service.

Routing configuration should be observable because incorrect routing can cause requests to reach the wrong service or fail before reaching the application.

## Authentication

The gateway can perform authentication checks before forwarding requests to downstream services.

Authentication at the gateway can reject requests that do not contain valid credentials. The gateway should avoid forwarding obviously unauthorized requests to downstream services.

Authentication establishes identity, while authorization determines whether that identity is permitted to perform a specific operation.

## Request Validation

Request validation prevents malformed payloads from reaching application services. Validation rules should be consistent with the contracts exposed by downstream APIs.

Rejecting malformed requests at the gateway can reduce unnecessary work in backend services.

## Rate Limiting

The gateway can also enforce rate limits. Rate limiting restricts how frequently a client or identity can make requests.

This protects downstream resources from excessive traffic and accidental request bursts.

## Correlation and Troubleshooting

The gateway should attach correlation identifiers so that a request can be followed across multiple services during troubleshooting.

A correlation ID can connect gateway logs with downstream application logs, database activity, and distributed traces.

## Gateway Failures

A gateway timeout does not necessarily mean that the downstream operation failed. Clients and operators should distinguish connection failures, gateway timeouts, and application-level errors when diagnosing incidents.

Gateway latency should therefore be monitored separately from downstream service latency.
