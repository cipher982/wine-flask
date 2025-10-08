#!/usr/bin/env python3
"""
Upload wine_data.db to MinIO.
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from minio import Minio

# Load environment from parent directory
project_dir = Path(__file__).parent.parent
load_dotenv(project_dir / ".env")


def upload_database():
    """Upload SQLite database to MinIO."""

    # Get MinIO credentials
    endpoint = os.environ.get("MINIO_ENDPOINT")
    access_key = os.environ.get("MINIO_ACCESS_KEY")
    secret_key = os.environ.get("MINIO_SECRET_KEY")

    if not all([endpoint, access_key, secret_key]):
        print("❌ Error: MinIO credentials not found in .env")
        sys.exit(1)

    # Initialize MinIO client
    client = Minio(endpoint, access_key=access_key, secret_key=secret_key, secure=True)

    bucket_name = "wine-data"
    db_file = project_dir / "wine_data.db"

    if not db_file.exists():
        print(f"❌ Error: Database file not found at {db_file}")
        sys.exit(1)

    # Create bucket if it doesn't exist
    if not client.bucket_exists(bucket_name):
        print(f"Creating bucket: {bucket_name}")
        client.make_bucket(bucket_name)

    # Upload database
    print(f"Uploading {db_file.name} to MinIO...")
    client.fput_object(bucket_name, "wine_data.db", str(db_file), content_type="application/x-sqlite3")

    # Verify upload
    stat = client.stat_object(bucket_name, "wine_data.db")
    size_mb = stat.size / (1024 * 1024)

    print("\n✅ Upload successful!")
    print(f"  Bucket: {bucket_name}")
    print("  Object: wine_data.db")
    print(f"  Size: {size_mb:.2f} MB")
    print(f"  Endpoint: {endpoint}")


if __name__ == "__main__":
    upload_database()
