import logging
import os
import random
import sys
from enum import Enum
from typing import TypeAlias

import psycopg2
from dotenv import load_dotenv
from flask import Flask
from flask import Response
from flask import render_template
from flask import send_file
from minio import Minio
from minio.error import S3Error
from psycopg2.extras import RealDictCursor

load_dotenv()

# Set constants
MINIO_BUCKET = "wine-bottles"
MINIO_ENDPOINT = os.environ.get("MINIO_ENDPOINT")
MINIO_ACCESS_KEY = os.environ.get("MINIO_ACCESS_KEY")
MINIO_SECRET_KEY = os.environ.get("MINIO_SECRET_KEY")
IMAGE_DIR = f"http://{MINIO_ENDPOINT}/{MINIO_BUCKET}/"


WineRecord: TypeAlias = dict[str, str | int | float]
BottleInfo: TypeAlias = tuple[int, str]


class WineCategory(Enum):
    BORDEAUX_RED_BLENDS = 1
    CABERNET_SAUVIGNON = 2
    CHARDONNAY = 3
    MERLOT = 4
    OTHER_RED_BLENDS = 5
    OTHER_WHITE_BLENDS = 6
    PINOT_GRIS_GRIGIO = 7
    PINOT_NOIR = 8
    RHONE_RED_BLENDS = 9
    RIESLING = 10
    ROSE = 11
    SANGIOVESE = 12
    SAUVIGNON_BLANC = 13
    SYRAH_SHIRAZ = 14
    ZINFANDEL = 15

    @property
    def display_name(self):
        return self.name.replace("_", " ").title()


# Initialize logger
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
LOG = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)


def get_minio_client():
    assert MINIO_ENDPOINT is not None, "MINIO_ENDPOINT is not set"
    return Minio(
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
        cursor_factory=RealDictCursor,
    )


def get_bottle_list() -> list[BottleInfo]:
    objects = get_minio_client().list_objects(MINIO_BUCKET, recursive=True)
    return [
        (int(obj.object_name.split("cat_")[1].split("_")[0]), obj.object_name) for obj in objects if obj.object_name
    ]


def sample_label_from_minio() -> BottleInfo:
    bottle_list = get_bottle_list()
    return random.choice(bottle_list)


def sample_from_postgresql(label_cat_2: int) -> WineRecord:
    category = WineCategory(label_cat_2)
    LOG.info(f"Sampling wine for category: {category.display_name}")
    conn = get_db_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT * FROM wine_descriptions WHERE category_2 = %s ORDER BY RANDOM() LIMIT 1",
                (category.display_name,),
            )
            result = cur.fetchone()
            if result is None:
                raise ValueError(f"No wine found for category: {category.display_name}")
    finally:
        conn.close()

    wine_record: WineRecord = dict(result)
    LOG.info(f"Returning wine: {wine_record['name']}")
    return wine_record


# API Image endpoint
@app.route("/image", methods=["GET"])
def serve_image():
    """
    This endpoint serves an image.
    """
    return send_file("./static/wine_logo_2.jpeg", mimetype="image/jpeg")


@app.route("/minio-image/<path:image_path>")
def serve_minio_image(image_path: str) -> Response:
    try:
        response = get_minio_client().get_object(MINIO_BUCKET, image_path)
        return Response(
            response.data,
            mimetype="image/png",
            headers={"Content-Disposition": f"inline; filename={image_path.split('/')[-1]}"},
        )
    except S3Error as e:
        return Response(f"Error retrieving image: {str(e)}", status=404)


@app.route("/")
@app.route("/wine")
def main() -> str:
    LOG.info("Starting request")

    # Sample a random wine label
    label_cat_2, label_path = sample_label_from_minio()
    image_path: str = f"/minio-image/{label_path}"
    LOG.info(f"Selected image path: {image_path}")

    wine: WineRecord = sample_from_postgresql(label_cat_2)
    LOG.info(f"Returning description for: {wine['name']}")

    return render_template(
        "index.html",
        w_name=wine["name"],
        w_category_1=wine["category_1"],
        w_category_2=wine["category_2"],
        w_origin=wine["origin"],
        w_description=wine["description"],
        w_image=image_path,
    )
