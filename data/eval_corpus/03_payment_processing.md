# Payment Processing and Retries

The payment service retries failed requests when failures appear to be transient. Network interruptions and downstream timeouts are examples of conditions that may recover after a short delay.

## Retry Configuration

MAX_RETRY_LIMIT controls the maximum number of retry attempts. The default value is 3.

Retry delays use exponential backoff. RETRY_BACKOFF_MS specifies the initial delay and defaults to 200 milliseconds. RETRY_BACKOFF_MULTIPLIER determines how the delay increases between attempts and defaults to 2.0.

Exponential backoff prevents a service from immediately sending repeated requests to a dependency that may already be overloaded.

## Why Retries Help

Retries can improve successful payment completion when a downstream service briefly becomes unavailable. The trade-off is additional latency and repeated work.

Retries are most appropriate for failures that are considered transient or safe to retry. A permanent validation error should generally not be retried repeatedly because the same request is unlikely to succeed without a change.

## Exhausted Retries

If all retry attempts are exhausted, the payment request is routed to a dead-letter queue for manual review.

A dead-letter queue prevents repeatedly failed work from blocking normal processing. Operators can inspect failed requests and determine whether a corrective action is required.

Retry limits and dead-letter handling are therefore related: the retry policy determines how many automatic attempts occur before the message enters a failure-handling path.

## Payment Safety

Payment operations should avoid creating duplicate charges when requests are retried. Idempotency mechanisms can associate repeated requests with the same logical operation.

The payment service should distinguish between a retry of the same operation and a genuinely new payment request.

## Monitoring

Payment retry counts, retry latency, downstream errors, and dead-letter queue depth are useful operational signals.

A sudden increase in retries can indicate network instability or a degraded downstream dependency even when the payment API continues returning successful responses for some requests.
