import asyncio
import json
from unittest.mock import Mock

import pytest

from memoized_lambda import MemoizedLambda, MemoizedLambdaError

FUNCTION_NAME = "test-function"
REQUEST_PAYLOAD = {}
RESPONSE_PAYLOAD = []


def serialize(obj):
    return json.dumps(obj, sort_keys=True).encode("utf-8")


@pytest.mark.parametrize("cache_result", (True, False))
@pytest.mark.asyncio
async def test_invoke_when_transform_returns_value(cache_result):
    lambda_client = Mock(invoke=Mock())
    memoized_lambda = MemoizedLambda(
        lambda_client,
        FUNCTION_NAME,
        {},
        lambda x: cache_result,
    )

    lambda_client.invoke.return_value = {
        "StatusCode": 200,
        "Payload": Mock(read=Mock(return_value=serialize(RESPONSE_PAYLOAD))),
    }

    result = await memoized_lambda.invoke(REQUEST_PAYLOAD)
    assert result == RESPONSE_PAYLOAD
    lambda_client.invoke.assert_called_once_with(FunctionName=FUNCTION_NAME, Payload=serialize(REQUEST_PAYLOAD))

    lambda_client.invoke.reset_mock()
    result = await memoized_lambda.invoke(REQUEST_PAYLOAD)
    assert result == RESPONSE_PAYLOAD
    if cache_result:
        lambda_client.invoke.assert_not_called()
    else:
        lambda_client.invoke.assert_called_once_with(FunctionName=FUNCTION_NAME, Payload=serialize(REQUEST_PAYLOAD))


@pytest.mark.parametrize("cache_result", (True, False))
@pytest.mark.asyncio
async def test_invoke_when_transform_raises_exception(cache_result):
    def response_transform(request, response):
        raise Exception()

    lambda_client = Mock(invoke=Mock())
    memoized_lambda = MemoizedLambda(
        lambda_client,
        FUNCTION_NAME,
        {},
        lambda x: cache_result,
        response_transform=response_transform,
    )

    lambda_client.invoke.return_value = {
        "StatusCode": 200,
        "Payload": Mock(read=Mock(return_value=serialize(RESPONSE_PAYLOAD))),
    }

    with pytest.raises(Exception):
        _ = await memoized_lambda.invoke(REQUEST_PAYLOAD)
    lambda_client.invoke.assert_called_once_with(FunctionName=FUNCTION_NAME, Payload=serialize(REQUEST_PAYLOAD))

    lambda_client.invoke.reset_mock()
    with pytest.raises(Exception):
        _ = await memoized_lambda.invoke(REQUEST_PAYLOAD)
    if cache_result:
        lambda_client.invoke.assert_not_called()
    else:
        lambda_client.invoke.assert_called_once_with(FunctionName=FUNCTION_NAME, Payload=serialize(REQUEST_PAYLOAD))


@pytest.mark.asyncio
async def test_invoke_should_raise_exception_on_status_error():
    lambda_client = Mock(invoke=Mock())
    memoized_lambda = MemoizedLambda(
        lambda_client,
        FUNCTION_NAME,
        {},
        lambda x: True,
    )

    lambda_client.invoke.return_value = {
        "StatusCode": 404,
    }

    with pytest.raises(MemoizedLambdaError):
        _ = await memoized_lambda.invoke(REQUEST_PAYLOAD)
    lambda_client.invoke.assert_called_once_with(FunctionName=FUNCTION_NAME, Payload=serialize(REQUEST_PAYLOAD))


@pytest.mark.asyncio
async def test_invoke_should_raise_exception_on_payload_read_error():
    lambda_client = Mock(invoke=Mock())
    memoized_lambda = MemoizedLambda(
        lambda_client,
        FUNCTION_NAME,
        {},
        lambda x: True,
    )

    lambda_client.invoke.return_value = {
        "StatusCode": 200,
        "Payload": Mock(read=Mock(side_effect=Exception())),
    }

    with pytest.raises(MemoizedLambdaError):
        _ = await memoized_lambda.invoke(REQUEST_PAYLOAD)
    lambda_client.invoke.assert_called_once_with(FunctionName=FUNCTION_NAME, Payload=serialize(REQUEST_PAYLOAD))


@pytest.mark.asyncio
async def test_concurrent_invoke_calls_should_invoke_lambda_once():
    lambda_client = Mock(invoke=Mock())
    memoized_lambda = MemoizedLambda(
        lambda_client,
        FUNCTION_NAME,
        {},
        lambda x: True,
    )

    lambda_client.invoke.return_value = {
        "StatusCode": 200,
        "Payload": Mock(read=Mock(return_value=serialize(RESPONSE_PAYLOAD))),
    }

    result = await asyncio.gather(
        memoized_lambda.invoke(REQUEST_PAYLOAD),
        memoized_lambda.invoke(REQUEST_PAYLOAD),
    )
    assert result[0] == RESPONSE_PAYLOAD
    assert result[1] == RESPONSE_PAYLOAD
    lambda_client.invoke.assert_called_once_with(FunctionName=FUNCTION_NAME, Payload=serialize(REQUEST_PAYLOAD))
