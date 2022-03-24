# Copyright 2022 Emanuele Giaquinta

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import annotations

import asyncio
import json
from collections.abc import Callable, MutableMapping
from typing import TYPE_CHECKING, Any, Generic, TypeVar, Union, cast

from botocore.exceptions import ClientError

if TYPE_CHECKING:
    from mypy_boto3_lambda.client import LambdaClient


class MemoizedLambdaError(Exception):
    pass


_T = TypeVar("_T")


class MemoizedLambda(Generic[_T]):
    def __init__(
        self,
        lambda_client: LambdaClient,
        function_name: str,
        cache: MutableMapping[bytes, asyncio.Task[_T]],
        cache_filter: Callable[[Union[_T, Exception]], bool] = lambda _x: True,
        request_transform: Callable[[Any], bytes] = lambda x: json.dumps(x, sort_keys=True).encode("utf-8"),
        response_transform: Callable[[bytes, bytes], _T] = lambda _x, y: cast(_T, json.loads(y)),
    ):
        self._lambda_client = lambda_client
        self._function_name = function_name
        self._cache = cache
        self._cache_filter = cache_filter
        self._request_transform = request_transform
        self._response_transform = response_transform

    def _invoke(self, payload: bytes) -> bytes:
        try:
            response = self._lambda_client.invoke(
                FunctionName=self._function_name,
                Payload=payload,
            )
        except ClientError as exc:
            raise MemoizedLambdaError("Failed to invoke lambda") from exc

        if response["StatusCode"] != 200:
            raise MemoizedLambdaError("Failed to invoke lambda", response)

        try:
            return response["Payload"].read()
        # pylint: disable-next=broad-except
        except Exception as exc:
            raise MemoizedLambdaError("Failed to read payload", response) from exc

    async def _invoke_and_transform(self, payload: bytes) -> _T:
        response = await asyncio.to_thread(self._invoke, payload)
        return self._response_transform(payload, response)

    async def invoke(self, payload: Any) -> _T:
        _payload = self._request_transform(payload)
        try:
            task = self._cache[_payload]
        except KeyError:
            pass
        else:
            try:
                result = await task
            except MemoizedLambdaError:
                pass
            # pylint: disable-next=broad-except
            except Exception as exc:
                if self._cache_filter(exc):
                    raise exc
            else:
                if self._cache_filter(result):
                    return result

        self._cache[_payload] = asyncio.create_task(self._invoke_and_transform(_payload))
        return await self._cache[_payload]
