import logging
import random
import os
import sys
from minio import Minio
from minio.error import S3Error

from flask import Flask, render_template, send_file, Response
from retry import retry
import psycopg2
from psycopg2.extras import RealDictCursor

from dotenv import load_dotenv

load_dotenv()

# Set constants
MINIO_BUCKET = "wine-bottles"
LABELS_PREFIX = "labels_on_bottle_v2/bottle_cat_"
MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY")
IMAGE_DIR = f"http://{MINIO_ENDPOINT}/{MINIO_BUCKET}/"
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

# Initialize Minio client
minio_client = Minio(
    MINIO_ENDPOINT,
    access_key=MINIO_ACCESS_KEY,
    secret_key=MINIO_SECRET_KEY,
    secure=False,
)

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

# Create list of bottles from Minio bucket
def get_bottle_list():
    objects = minio_client.list_objects(
        MINIO_BUCKET,
        recursive=True
    )
    return [(int(obj.object_name.split("cat_")[1].split("_")[0]), obj.object_name) for obj in objects]

def sample_label_from_minio():
    bottle_list = get_bottle_list()
    return random.choice(bottle_list)

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

# API Image endpoint
@app.route("/image", methods=["GET"])
def serve_image():
    """
    This endpoint serves an image.
    """
    return send_file("./static/wine_logo_2.jpeg", mimetype="image/jpeg")

@app.route("/minio-image/<path:image_path>")
def serve_minio_image(image_path):
    try:
        response = minio_client.get_object(MINIO_BUCKET, image_path)
        return Response(
            response.data,
            mimetype="image/png",
            headers={"Content-Disposition": f"inline; filename={image_path.split('/')[-1]}"}
        )
    except S3Error as e:
        return f"Error retrieving image: {str(e)}", 404


@app.route("/")
@app.route("/wine")
@retry((Exception), tries=5, delay=0, backoff=0)
def main():
    LOG.info("Starting request")

    # Sample a random wine label
    label_cat_2, label_path = sample_label_from_minio()
    image_path = f"/minio-image/{label_path}"
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