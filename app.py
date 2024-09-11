import logging
import os
import random
import sys
from enum import Enum
from typing import TypeAlias

import psycopg2
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Request
from fastapi.responses import FileResponse
from fastapi.responses import HTMLResponse
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from minio import Minio
from minio.error import S3Error
from psycopg2.extras import RealDictCursor
from pydantic import BaseModel

load_dotenv()

# Set constants
MINIO_BUCKET = "wine-bottles"
IMAGE_DIR = f"http://{os.environ.get('MINIO_ENDPOINT')}/{MINIO_BUCKET}/"

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


class Settings(BaseModel):
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    db_host: str
    db_port: str
    db_name: str
    db_user: str
    db_password: str

    class Config:
        env_file = ".env"


settings = Settings(
    minio_endpoint=os.environ["MINIO_ENDPOINT"],
    minio_access_key=os.environ["MINIO_ACCESS_KEY"],
    minio_secret_key=os.environ["MINIO_SECRET_KEY"],
    db_host=os.environ["DB_HOST"],
    db_port=os.environ["DB_PORT"],
    db_name=os.environ["DB_NAME"],
    db_user=os.environ["DB_USER"],
    db_password=os.environ["DB_PASSWORD"],
)
# Initialize logger
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
LOG = logging.getLogger(__name__)

# Initialize FastAPI app
app = FastAPI()

# Set up static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Set up Jinja2 templates
templates = Jinja2Templates(directory="templates")


def get_minio_client():
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=False,
    )


def get_db_connection():
    try:
        conn = psycopg2.connect(
            host=settings.db_host,
            port=settings.db_port,
            database=settings.db_name,
            user=settings.db_user,
            password=settings.db_password,
            cursor_factory=RealDictCursor,
            connect_timeout=3,
        )
        LOG.info("Database connection successful")
        return conn
    except psycopg2.Error as e:
        LOG.error(f"Unable to connect to the database: {e}")
        raise


@app.get("/db-health")
async def db_health_check():
    try:
        conn = get_db_connection()
        with conn.cursor() as cur:
            cur.execute("SELECT 1")
        conn.close()
        return {"status": "ok"}
    except Exception as e:
        LOG.error(f"Database health check failed: {e}")
        raise HTTPException(status_code=500, detail=str(e)) from e


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
                raise HTTPException(status_code=404, detail=f"No wine found for category: {category.display_name}")
    finally:
        conn.close()

    wine_record: WineRecord = dict(result)
    LOG.info(f"Returning wine: {wine_record['name']}")
    return wine_record


@app.get("/image", response_class=FileResponse)
async def serve_image():
    """
    This endpoint serves an image.
    """
    return FileResponse("./static/wine_logo_2.jpeg", media_type="image/jpeg")


@app.get("/minio-image/{image_path:path}")
async def serve_minio_image(image_path: str):
    try:
        response = get_minio_client().get_object(MINIO_BUCKET, image_path)
        return Response(
            content=response.data,
            media_type="image/png",
            headers={"Content-Disposition": f"inline; filename={image_path.split('/')[-1]}"},
        )
    except S3Error as e:
        raise HTTPException(status_code=404, detail=f"Error retrieving image: {str(e)}") from e


@app.get("/", response_class=HTMLResponse)
@app.get("/wine", response_class=HTMLResponse)
async def main(request: Request):
    LOG.info("Starting request")

    # Sample a random wine label
    label_cat_2, label_path = sample_label_from_minio()
    image_path: str = f"/minio-image/{label_path}"
    LOG.info(f"Selected image path: {image_path}")

    wine: WineRecord = sample_from_postgresql(label_cat_2)
    LOG.info(f"Returning description for: {wine['name']}")

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "w_name": wine["name"],
            "w_category_1": wine["category_1"],
            "w_category_2": wine["category_2"],
            "w_origin": wine["origin"],
            "w_description": wine["description"],
            "w_image": image_path,
        },
    )
