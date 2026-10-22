# Message Queues

Message queues allow producers and consumers to communicate asynchronously.

A producer places a message onto a queue, while a consumer retrieves and processes the message later. This separation allows the producer to continue without waiting for the consumer to finish.

## Workload Smoothing

Queues can absorb temporary workload spikes when consumers cannot process messages as quickly as producers generate them.

Instead of forcing the producer to wait for immediate processing, the queue stores pending work until a consumer becomes available.

Queue depth can therefore increase temporarily during bursts without necessarily indicating a failure.

## Retries and Dead-Letter Queues

A dead-letter queue stores messages that cannot be successfully processed after the configured retry policy has been exhausted.

Retry policies should distinguish temporary dependency failures from permanent processing errors.

Repeated retries can consume worker capacity and increase queue latency. A maximum retry limit prevents one problematic message from being retried indefinitely.

## Acknowledgement

Message acknowledgement determines when a consumer tells the queue that processing has completed.

Acknowledging too early can cause failed work to be lost, while acknowledging too late can result in duplicate processing.

Consumers should therefore be designed with idempotency where repeated processing is possible.

## Queue Monitoring

Queue depth is an important operational signal. A continuously increasing queue depth can indicate that consumers are unable to keep up with incoming workload.

Other useful measurements include message age, processing latency, retry count, acknowledgement failures, and dead-letter queue size.

## Delivery Semantics

Queue systems may provide different delivery guarantees. At-least-once processing can result in duplicate delivery, making idempotent consumers particularly important.

Exactly-once behavior is more difficult to guarantee across distributed systems and should not be assumed simply because a message broker acknowledges a message.
