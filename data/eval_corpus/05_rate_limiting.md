# Rate Limiting

Rate limiting controls how frequently a client or identity can make requests to a service during a defined period.

A rate limiter can protect backend resources from excessive traffic and reduce the effect of accidental request bursts.

## Rate Limit Identity

Rate limits can be associated with a user, API key, IP address, or another identity depending on the application's requirements.

Choosing the identity determines which requests share the same limit. An API-key-based limit can provide separate quotas for different customers, while an IP-based limit groups requests by network address.

## Algorithms

A token bucket algorithm allows a defined number of requests to be handled immediately while replenishing capacity over time.

A fixed-window algorithm instead counts requests inside discrete time intervals. Fixed windows are simple to implement but can allow bursts near the boundary between two windows.

Different algorithms therefore produce different traffic patterns even when their configured limits appear similar.

## HTTP Behavior

When a request exceeds the configured limit, the API commonly returns an HTTP 429 response.

The response may include information indicating when the client should retry. Clients should avoid immediately sending another request when the service has explicitly indicated that the limit has been exceeded.

## Distributed Systems

Distributed rate limiting requires shared state or coordination between service instances.

A local in-memory limiter can produce inconsistent limits when traffic is distributed across multiple application instances because each instance sees only part of the total request volume.

A shared limiter can provide a more consistent global limit but introduces an additional dependency and network overhead.

## Caching Relationship

Rate limiting and caching solve different problems. Caching can reduce repeated backend work for identical reads, while rate limiting restricts how quickly requests are accepted.

A cached response may reduce database traffic without changing the number of requests accepted by the API gateway.

## Monitoring

Useful rate-limiting metrics include rejected requests, requests per identity, current bucket utilization, and response status distributions.
