import time
from typing import Any
import boto3
from boto3.dynamodb.types import TypeDeserializer

from functools import lru_cache


TABLE_SCAN_CACHE_TIME_SECONDS = 60 * 10

ddb = boto3.client('dynamodb')
s3 = boto3.client('s3')

deserializer = TypeDeserializer()

def unmarshall(obj: dict[str, Any]) -> dict[str, Any]:
    return {k: deserializer.deserialize(v) for k, v in obj.items()}

@lru_cache()
def _scan_table(table_name: str, ttl_hash: int | None = None) -> list[dict[str, Any]]:
    """
    Perform a full scan on a DynamoDB table.

    ttl_hash exists to support a time-based cache
    """
    del ttl_hash
    return [
        unmarshall(item)
        for page in ddb.get_paginator('scan').paginate(TableName=table_name)
        for item in page['Items']
    ]

def scan_table(table_name: str) -> list[dict[str, Any]]:
    # This will return the same value for every call within TABLE_SCAN_CACHE_TIME_SECONDS
    ttl_hash=round(time.time() / TABLE_SCAN_CACHE_TIME_SECONDS)
    return _scan_table(table_name, ttl_hash=ttl_hash)

def get_presigned_url(bucket: str, key: str) -> str:
    return s3.generate_presigned_url('get_object', Params={'Bucket': bucket, 'Key': key}, ExpiresIn=3600)
