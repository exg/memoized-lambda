# Memoized Lambda

MemoizedLambda is a class that provides an async invoke interface with
deduplication of requests and memoization of responses for a [Boto3 Lambda
Client](https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/lambda.html).

## Usage

First, create a cache for the memoization:

```python
from cachetools import TTLCache
cache = TTLCache(ttl=60, maxsize=1024)
```

The cache can be any object that implements `collections.abc.MutableMapping`.

Then, create a lambda client and a memoized lambda for some AWS Lambda function:

```python
import boto3
from memoized_lambda import MemoizedLambda
client = boto3.client("lambda")
mlambda = MemoizedLambda(lambda_client=client, function_name="function", cache=cache)
```

Finally, invoke the lambda function:

```python
import asyncio
loop = asyncio.get_event_loop()
coro = asyncio.gather(mlambda.invoke({}), mlambda.invoke([]), mlambda.invoke({}))
loop.run_until_complete(coro)
```

`invoke` returns the response payload, or raises a `MemoizedLambdaError`
exception on error. The first invocation with a given input will invoke the
lambda, while subsequent invocations for the same input will read the response
payload from the cache. In the above example, the lambda is invoked once for
`{}` and once for `[]`.

The request and response payloads are transformed using configurable transform
functions that default to JSON serialization and deserialization. If you want to
override them, use the optional `request_transform` and `response_transform`
arguments:

```python
mlambda = MemoizedLambda(
    lambda_client=client,
    function_name="function",
    cache=cache,
    request_transform=lambda x: x,
    response_transform=lambda x, y: y)
```

The `response_transform` function gets the request and response payload as
arguments.

If you want to avoid caching some responses, use the optional `cache_filter`
argument:

```python
mlambda = MemoizedLambda(
    lambda_client=client,
    function_name="function",
    cache=cache,
    cache_filter=lambda x: not isinstance(x, Exception))
```

Note that `MemoizedLambdaError` exceptions are never cached, even if raised by
the response transform.
