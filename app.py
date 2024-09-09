import json
import logging
import random
import os
import sys
from minio import Minio
from minio.error import S3Error
import io

from flask import Flask, render_template, jsonify, send_file
from google.cloud import storage
from google.oauth2 import service_account
from retry import retry
import psycopg2
from psycopg2.extras import RealDictCursor

from dotenv import load_dotenv

load_dotenv()

# Set constants
GCLOUD_BUCKET = "wine-flask"
LABELS_BLOB = "labels_on_bottle_v2/bottle_cat_"
DATASET_DIR = f"https://storage.googleapis.com/{GCLOUD_BUCKET}/descriptions/"
IMAGE_DIR = f"https://storage.googleapis.com/{GCLOUD_BUCKET}/"
FIRESTORE_COLLECTION = "gpt2-xl-outputs"
CAT_2_DICT = {
    1: "Bordeaux Red Blends",
    2: "Cabernet Sauvignon",
    3: "Chardonnay",
    4: "Merlot",
    5: "Other Red Blends",
    6: "Other White Blends",
    7: "Pinot Gris/Grigio",
    8: "Pinot Noir",
    9: "Rhone Red Blends",
    10: "Riesling",
    11: "Rosé",
    12: "Sangiovese",
    13: "Sauvignon Blanc",
    14: "Syrah/Shiraz",
    15: "Zinfandel",
}


# Initialize logger
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
LOG = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# psql
def get_db_connection():
    return psycopg2.connect(
        host=os.environ.get("DB_HOST", "localhost"),
        port=os.environ.get("DB_PORT", "5432"),
        database=os.environ.get("DB_NAME", "postgres"),
        user=os.environ.get("DB_USER", "postgres"),
        password=os.environ.get("DB_PASSWORD"),
        cursor_factory=RealDictCursor
    )

# Initialize google.cloud client
gcloud_creds = service_account.Credentials.from_service_account_file(".gcreds")

# Create list of bottles from gcloud blob
storage_client = storage.Client(credentials=gcloud_creds)
blobs = storage_client.list_blobs(GCLOUD_BUCKET, prefix=LABELS_BLOB, delimiter=None)
blobs = [(int(i.name.split("cat_")[1].split("_")[0]), i.name) for i in blobs]


def sample_label_from_gcs():
    return random.choice(blobs)


def sample_from_postgresql(return_random=True, label_cat_2=None, doc_id=None):
    LOG.info("Starting PostgreSQL sample")
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            if return_random:
                cur.execute(
                    "SELECT * FROM wine_descriptions WHERE category_2 = %s ORDER BY RANDOM() LIMIT 1",
                    (CAT_2_DICT[label_cat_2],)
                )
            else:
                cur.execute(
                    "SELECT * FROM wine_descriptions WHERE category_2 = %s LIMIT 1",
                    (CAT_2_DICT[label_cat_2],)
                )
            result = cur.fetchone()
    finally:
        conn.close()

    LOG.info(f"Returning PostgreSQL sample: {result}")
    return result

# chatgpt plugin
@app.route("/.well-known/ai-plugin.json")
def get_stuff():
    with open("./.well-known/ai-plugin.json", "r") as f:
        data = json.load(f)
    return jsonify(data)


# OpenAPI yaml spec
@app.route("/openapi.yaml")
def openapi():
    with open("./openapi/image-api.yaml", "r") as f:
        data = f.read()
    return data


# API Image endpoint
@app.route("/image", methods=["GET"])
def serve_image():
    """
    This endpoint serves an image.
    """
    return send_file("./static/wine_logo_2.jpeg", mimetype="image/jpeg")


@app.route("/")
@app.route("/wine")
@retry((Exception), tries=5, delay=0, backoff=0)
def main():
    LOG.info("Starting request")

    # Sample a random wine label
    label_cat_2, label_path = sample_label_from_gcs()
    image_path = IMAGE_DIR + label_path
    LOG.info(f"Returning image path: {image_path}")

    wine = None
    while wine is None:
        wine = sample_from_postgresql(return_random=True, label_cat_2=label_cat_2)
        wine_name = wine["name"]
        wine_category_1 = wine["category_1"]
        wine_category_2 = wine["category_2"]
        wine_origin = wine["origin"]
        wine_description = wine["description"]
    LOG.info(f"Returning description for: {wine_name}")

    return render_template(
        "index.html",
        w_name=wine_name,
        w_category_1=wine_category_1,
        w_category_2=wine_category_2,
        w_origin=wine_origin,
        w_description=wine_description,
        w_image=image_path,
    )
