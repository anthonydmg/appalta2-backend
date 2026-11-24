
import os

import boto3
from botocore.config import Config
from dotenv import load_dotenv
from botocore.exceptions import ClientError

load_dotenv()

RUSTFS_ENDPOINT = os.getenv("RUSTFS_ENDPOINT")
RUSTFS_ACCESS_KEY = os.getenv("RUSTFS_ACCESS_KEY")
RUSTFS_SECRET_KEY = os.getenv("RUSTFS_SECRET_KEY")
RUSTFS_BUCKET = os.getenv("RUSTFS_BUCKET")
RUSTFS_REGION = os.getenv("RUSTFS_REGION", "us-east-1")


def get_rustfs_client():
    """Crea un cliente S3 para conectarse a RustFS."""

    return boto3.client(
        "s3",
        endpoint_url=RUSTFS_ENDPOINT,
        aws_access_key_id=RUSTFS_ACCESS_KEY,
        aws_secret_access_key=RUSTFS_SECRET_KEY,
        region_name=RUSTFS_REGION,
        config=Config(
            signature_version="s3v4",
            s3={"addressing_style": "path"}
        )
    )


def upload_file(
    local_path: str,
    object_key: str,
    content_type: str = "application/octet-stream"
):
    """Sube un archivo local a RustFS."""

    client = get_rustfs_client()

    client.upload_file(
        local_path,
        RUSTFS_BUCKET,
        object_key,
        ExtraArgs={
            "ContentType": content_type
        }
    )

    return {
        "uploaded": True,
        "bucket": RUSTFS_BUCKET,
        "object_key": object_key,
        "content_type": content_type,
        "s3_path": f"s3://{RUSTFS_BUCKET}/{object_key}"
    }


def object_exists(object_key: str) -> bool:
    """Comprueba si existe un objeto en RustFS."""

    client = get_rustfs_client()

    try:
        client.head_object(
            Bucket=RUSTFS_BUCKET,
            Key=object_key
        )
        return True

    except ClientError as error:
        status = error.response.get(
            "ResponseMetadata", {}
        ).get("HTTPStatusCode")

        if status == 404:
            return False

        raise


def list_objects(prefix: str = ""):
    """Lista los objetos almacenados bajo una ruta."""

    client = get_rustfs_client()
    paginator = client.get_paginator("list_objects_v2")

    objects = []

    for page in paginator.paginate(
        Bucket=RUSTFS_BUCKET,
        Prefix=prefix
    ):
        for item in page.get("Contents", []):
            objects.append({
                "key": item["Key"],
                "size": item["Size"],
                "last_modified": item["LastModified"].isoformat()
            })

    return objects


def delete_file(object_key: str):
    """Elimina un objeto de RustFS."""

    client = get_rustfs_client()

    client.delete_object(
        Bucket=RUSTFS_BUCKET,
        Key=object_key
    )

    return {
        "deleted": True,
        "bucket": RUSTFS_BUCKET,
        "object_key": object_key
    }


def download_file(object_key: str, local_path: str):
    """Descarga un objeto de RustFS a una ruta local."""

    client = get_rustfs_client()

    client.download_file(
        RUSTFS_BUCKET,
        object_key,
        local_path
    )

    return {
        "downloaded": True,
        "bucket": RUSTFS_BUCKET,
        "object_key": object_key,
        "local_path": local_path
    }

def test_rustfs_connection():
    """Comprueba la conexión y el acceso al bucket."""

    client = get_rustfs_client()

    response = client.list_buckets()

    buckets = [
        bucket["Name"]
        for bucket in response.get("Buckets", [])
    ]

    if RUSTFS_BUCKET not in buckets:
        raise Exception(
            f"No se encontró el bucket: {RUSTFS_BUCKET}"
        )

    return {
        "connected": True,
        "bucket": RUSTFS_BUCKET,
        "available_buckets": buckets
    }


def get_file_content(object_key: str) -> bytes:
    client = get_rustfs_client()

    response = client.get_object(
        Bucket=RUSTFS_BUCKET,
        Key=object_key
    )

    return response["Body"].read()