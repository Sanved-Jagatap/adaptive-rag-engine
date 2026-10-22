# Response Caching

The API layer can cache read-heavy GET responses to reduce database load during periods of high traffic. Caching is useful when the same data is requested repeatedly and the cost of retrieving that data from the primary database is significant.

## Cache Lifetime

CACHE_TTL_SECONDS controls how long a cached response remains valid before it becomes stale. The default value is 120 seconds.

A longer TTL can reduce database traffic because cached responses remain available for more requests. The trade-off is that information can remain stale for longer.

A shorter TTL improves freshness but increases the number of requests that eventually reach the database.

## Cache Capacity

CACHE_MAX_ENTRIES limits the number of distinct cache keys stored by the cache. The default value is 10000 entries.

CACHE_EVICTION_POLICY determines which entries are removed when the cache reaches capacity. The default policy is LRU, or least recently used.

An eviction policy becomes important when the cache reaches its configured capacity. Frequently accessed entries should generally remain available while less useful entries are removed.

## Cache Invalidation

Write operations that modify cached resources should invalidate the affected cache keys explicitly. This prevents a recently changed resource from remaining visible through an old cached response.

TTL and explicit invalidation solve different aspects of cache freshness. TTL provides an upper bound on how long an unchanged cached entry can remain available, while invalidation can remove affected entries immediately after a write.

## Cache Failures

A cache failure should not normally prevent a read operation from reaching the primary database. The application should be able to fall back to the database when the cache is unavailable.

Cache failures should be observable because repeated failures can increase database traffic and change application latency.

## Performance Trade-offs

Caching can reduce database work, but it introduces memory usage, invalidation complexity, and possible stale responses. Cache configuration should therefore be evaluated together with database load, response latency, and freshness requirements.
