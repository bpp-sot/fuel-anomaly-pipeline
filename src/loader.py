"""Data loading module for fuel logs.

Handles CSV file reading from local disk or AWS S3, with path validation
and initial DataFrame creation.
"""

import io
from pathlib import Path
from typing import Optional
import pandas as pd


class LoaderError(Exception):
    """Custom exception for data loading errors."""
    pass


def load_fuel_data(file_path: str, encoding: str = "utf-8") -> pd.DataFrame:
    """Load fuel consumption data from CSV file.
    
    Args:
        file_path: Path to the CSV file containing fuel logs
        encoding: File encoding (default: utf-8)
        
    Returns:
        DataFrame with fuel log data
        
    Raises:
        LoaderError: If file doesn't exist, is empty, or cannot be read
    """
    path = Path(file_path)
    
    if not path.exists():
        raise LoaderError(f"File not found: {file_path}")
    
    if not path.is_file():
        raise LoaderError(f"Path is not a file: {file_path}")
    
    if path.stat().st_size == 0:
        raise LoaderError(f"File is empty: {file_path}")
    
    try:
        df = pd.read_csv(path, encoding=encoding)
    except pd.errors.EmptyDataError:
        raise LoaderError(f"CSV file contains no data: {file_path}")
    except pd.errors.ParserError as e:
        raise LoaderError(f"Failed to parse CSV file: {e}")
    except Exception as e:
        raise LoaderError(f"Unexpected error loading file: {e}")
    
    if df.empty:
        raise LoaderError(f"Loaded DataFrame is empty: {file_path}")
    
    return df


def load_fuel_data_from_s3(s3_url: str, encoding: str = "utf-8") -> pd.DataFrame:
    """Load fuel consumption data from an S3 object.

    Args:
        s3_url: S3 URL in the form s3://bucket-name/path/to/file.csv
        encoding: File encoding (default: utf-8)

    Returns:
        DataFrame with fuel log data

    Raises:
        LoaderError: If the URL is malformed, the object does not exist,
                     the body is empty, or the CSV cannot be parsed
    """
    try:
        import boto3
        from botocore.exceptions import ClientError
    except ImportError:
        raise LoaderError(
            "boto3 is required for S3 loading. "
            "Install it with: pip install boto3"
        )

    if not s3_url.startswith("s3://"):
        raise LoaderError(
            f"Invalid S3 URL (must start with s3://): {s3_url}"
        )

    path_part = s3_url[len("s3://"):]
    if "/" not in path_part:
        raise LoaderError(
            f"Invalid S3 URL (no object key found): {s3_url}"
        )

    bucket, key = path_part.split("/", 1)

    if not bucket:
        raise LoaderError(f"Invalid S3 URL (empty bucket name): {s3_url}")
    if not key:
        raise LoaderError(f"Invalid S3 URL (empty object key): {s3_url}")

    s3 = boto3.client("s3")

    try:
        response = s3.get_object(Bucket=bucket, Key=key)
    except ClientError as e:
        code = e.response["Error"]["Code"]
        if code in ("NoSuchKey", "404"):
            raise LoaderError(f"S3 object not found: s3://{bucket}/{key}")
        if code in ("NoSuchBucket",):
            raise LoaderError(f"S3 bucket not found: {bucket}")
        if code in ("AccessDenied", "403"):
            raise LoaderError(
                f"Access denied to s3://{bucket}/{key}. "
                "Check AWS credentials and bucket permissions."
            )
        raise LoaderError(f"Failed to retrieve from S3: {e}")
    except Exception as e:
        raise LoaderError(f"Unexpected error fetching from S3: {e}")

    body = response["Body"].read()

    if not body:
        raise LoaderError(f"S3 object is empty: s3://{bucket}/{key}")

    try:
        df = pd.read_csv(io.BytesIO(body), encoding=encoding)
    except pd.errors.EmptyDataError:
        raise LoaderError(f"CSV in S3 contains no data: s3://{bucket}/{key}")
    except pd.errors.ParserError as e:
        raise LoaderError(f"Failed to parse CSV from S3: {e}")
    except Exception as e:
        raise LoaderError(f"Unexpected error parsing CSV from S3: {e}")

    if df.empty:
        raise LoaderError(
            f"Loaded DataFrame is empty: s3://{bucket}/{key}"
        )

    return df


def load_with_config(config: Optional[dict] = None) -> pd.DataFrame:
    """Load fuel data using configuration dictionary.
    
    Args:
        config: Optional configuration with 'data_path' and 'encoding' keys
        
    Returns:
        DataFrame with fuel log data
    """
    if config is None:
        config = {}
    
    data_path = config.get("data_path", "data/sample_fuel_logs.csv")
    encoding = config.get("encoding", "utf-8")
    
    return load_fuel_data(data_path, encoding)
