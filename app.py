import logging
import os
import random
import sqlite3
import sys
from enum import Enum
from pathlib import Path
from typing import TypeAlias

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi import HTTPException
from fastapi import Request
from fastapi import status
from fastapi.responses import FileResponse
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from minio import Minio
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

    class Config:
        env_file = ".env"


settings = Settings(
    minio_endpoint=os.environ["MINIO_ENDPOINT"],
    minio_access_key=os.environ["MINIO_ACCESS_KEY"],
    minio_secret_key=os.environ["MINIO_SECRET_KEY"],
)
# Initialize logger
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
LOG = logging.getLogger(__name__)

# Database path
DB_PATH = Path("/tmp/wine_data.db")


def download_database_from_minio():
    """Download SQLite database from MinIO at startup."""
    if DB_PATH.exists():
        LOG.info(f"Database already exists at {DB_PATH}")
        return

    LOG.info("Downloading wine database from MinIO...")
    try:
        client = get_minio_client()
        client.fget_object("wine-data", "wine_data.db", str(DB_PATH))
        LOG.info(f"✅ Database downloaded successfully to {DB_PATH}")
    except Exception as e:
        LOG.error(f"❌ Failed to download database from MinIO: {e}")
        raise


# Initialize FastAPI app
app = FastAPI()


# Download database on startup
@app.on_event("startup")
def startup_event():
    download_database_from_minio()


# Set up static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Set up Jinja2 templates
templates = Jinja2Templates(directory="templates")


def get_minio_client():
    return Minio(
        settings.minio_endpoint,
        access_key=settings.minio_access_key,
        secret_key=settings.minio_secret_key,
        secure=True,
    )


def get_db_connection():
    """Get SQLite database connection."""
    try:
        conn = sqlite3.connect(f"file:{DB_PATH}?mode=ro", uri=True, check_same_thread=False)
        conn.row_factory = sqlite3.Row  # Return rows as dict-like objects
        conn.execute("PRAGMA query_only = ON")
        conn.execute("PRAGMA cache_size = 10000")
        return conn
    except sqlite3.Error as e:
        LOG.error(f"Unable to connect to the database: {e}")
        raise


def get_bottle_list() -> list[BottleInfo]:
    objects = get_minio_client().list_objects(MINIO_BUCKET, recursive=True)
    return [
        (int(obj.object_name.split("cat_")[1].split("_")[0]), obj.object_name) for obj in objects if obj.object_name
    ]


def sample_label_from_minio() -> BottleInfo:
    bottle_list = get_bottle_list()
    return random.choice(bottle_list)


def sample_from_sqlite(label_cat_2: int) -> WineRecord:
    """Sample a wine from SQLite database by category."""
    category = WineCategory(label_cat_2)
    LOG.info(f"Sampling wine for category: {category.display_name}")
    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute(
            "SELECT * FROM wine_descriptions WHERE category_2 = ? ORDER BY RANDOM() LIMIT 1",
            (category.display_name,),
        )
        result = cur.fetchone()
        if result is None:
            LOG.warning(f"No wine found for category: {category.display_name}. Sampling from all categories.")
            cur.execute("SELECT * FROM wine_descriptions ORDER BY RANDOM() LIMIT 1")
            result = cur.fetchone()
            if result is None:
                raise HTTPException(status_code=500, detail="No wines found in the database")
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


@app.get("/", response_class=HTMLResponse)
@app.head("/", response_class=HTMLResponse)
@app.get("/wine", response_class=HTMLResponse)
@app.head("/wine", response_class=HTMLResponse)
async def main(request: Request):
    LOG.info("Starting request")

    # Sample a random wine label
    label_cat_2, label_path = sample_label_from_minio()
    # Use direct MinIO URL instead of proxy endpoint
    image_path: str = f"{IMAGE_DIR}{label_path}"
    LOG.info(f"Selected image path: {image_path}")

    wine: WineRecord = sample_from_sqlite(label_cat_2)
    LOG.info(f"Returning description for: {wine['name']}")

    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "w_name": wine["name"],
            "w_category_2": wine["category_2"],
            "w_origin": wine["origin"],
            "w_description": wine["description"],
            "w_image": image_path,
        },
    )


@app.get("/health", status_code=status.HTTP_200_OK)
async def health_check():
    health_status = {"database": "unhealthy", "minio": "unhealthy"}

    # Check database connection
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT 1")
        conn.close()
        health_status["database"] = "healthy"
    except Exception as e:
        LOG.error(f"Database health check failed: {e}")

    # Check MinIO connection
    try:
        minio_client = get_minio_client()
        minio_client.list_buckets()
        health_status["minio"] = "healthy"
    except Exception as e:
        LOG.error(f"MinIO health check failed: {e}")

    if all(status == "healthy" for status in health_status.values()):
        return health_status
    else:
        raise HTTPException(status_code=503, detail=health_status)
