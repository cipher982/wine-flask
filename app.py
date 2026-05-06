import logging
import os
import random
import sqlite3
import sys
from datetime import date
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
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from minio import Minio
from pydantic import BaseModel

load_dotenv()

# Set constants
MINIO_BUCKET = "wine-bottles"
IMAGE_DIR = f"https://{os.environ.get('MINIO_ENDPOINT')}/{MINIO_BUCKET}/"
SITE_URL = os.environ.get("SITE_URL", "https://thiswinedoesnotexist.com").rstrip("/")
DEFAULT_TITLE = "This Wine Does Not Exist - AI Wine Generator"
DEFAULT_DESCRIPTION = (
    "Generate fictional wines with AI-created names, tasting notes, origins, and bottle labels from an old machine "
    "learning art project."
)
WineRecord: TypeAlias = dict[str, str | int | float]
BottleInfo: TypeAlias = tuple[int, str]
SEOPage: TypeAlias = dict[str, str | list[str]]
BOTTLE_LIST: list[BottleInfo] = []
SEO_PAGES: dict[str, SEOPage] = {
    "/ai-wine-generator": {
        "title": "AI Wine Generator - This Wine Does Not Exist",
        "description": "Use a random AI wine generator to create fictional wine names, tasting notes, origins, and bottle labels.",
        "heading": "AI Wine Generator",
        "intro": (
            "This AI wine generator creates a new fictional bottle every time the page reloads. It combines older "
            "machine learning models for wine names, descriptions, and label images into one fake wine page."
        ),
        "body": (
            "The generated wines are not real products and are not meant as buying advice. They are synthetic wine "
            "branding artifacts: plausible names, strange tasting notes, fake origins, and AI-created labels."
        ),
        "items": [
            "Generate a fictional wine name and vintage",
            "Pair it with a generated bottle label",
            "Create a fake origin, category, and tasting note",
            "Reload the generator for a new result",
        ],
    },
    "/fake-wine-name-generator": {
        "title": "Fake Wine Name Generator - This Wine Does Not Exist",
        "description": "Generate strange fictional wine names from an old neural network wine project.",
        "heading": "Fake Wine Name Generator",
        "intro": (
            "The original project trained character-level neural networks on wine names so the output feels close "
            "to real wine branding while still being obviously synthetic."
        ),
        "body": (
            "A fake wine name works best when it almost sounds like something from a cellar, catalog, or tasting "
            "room. This site keeps that slightly broken quality instead of polishing every result into modern AI copy."
        ),
        "items": [
            "Invented chateau and vineyard names",
            "Synthetic vintages and bottle names",
            "Category-aware pairings with generated labels",
            "A deliberately odd old-internet generator style",
        ],
    },
    "/ai-wine-label-generator": {
        "title": "AI Wine Label Generator - This Wine Does Not Exist",
        "description": "See AI-generated wine bottle labels from a StyleGAN-era generative art project.",
        "heading": "AI Wine Label Generator",
        "intro": (
            "This project includes AI-generated wine bottle labels created as part of a StyleGAN-era experiment. "
            "Each label is selected from the stored bottle image set and paired with generated wine text."
        ),
        "body": (
            "The label generator is intentionally simple: it presents generated bottle art rather than trying to "
            "build a professional design suite. The appeal is the weirdness of synthetic wine packaging."
        ),
        "items": [
            "Generated bottle labels grouped by wine category",
            "Direct HTTPS image URLs for fast loading",
            "Fixed dimensions for stable page layout",
            "Random pairing with generated names and tasting notes",
        ],
    },
    "/wine-tasting-note-generator": {
        "title": "Wine Tasting Note Generator - This Wine Does Not Exist",
        "description": "Generate fictional wine descriptions and tasting notes from a GPT-2 wine text experiment.",
        "heading": "Wine Tasting Note Generator",
        "intro": (
            "The wine descriptions come from a language model trained on a large set of wine text. The result is a "
            "fictional tasting note that often has the rhythm of wine writing without describing a real bottle."
        ),
        "body": (
            "The output can be funny, oddly specific, or almost believable. That is the point: a tasting note "
            "generator is most interesting when it reveals the formula of wine description language."
        ),
        "items": [
            "Generated tasting notes for fictional wines",
            "Synthetic winery-style descriptions",
            "Random category and origin details",
            "A visible link back to the model/code history",
        ],
    },
    "/about": {
        "title": "About This Wine Does Not Exist",
        "description": "Background on This Wine Does Not Exist, an older AI wine name, description, and label generation project.",
        "heading": "About This Wine Does Not Exist",
        "intro": (
            "This Wine Does Not Exist is a small AI art project by David Rose. It started as a data collection and "
            "model-training experiment using wine names, descriptions, and bottle label images."
        ),
        "body": (
            "The current site is a lightweight FastAPI app that serves the generated content from SQLite and MinIO. "
            "It preserves the original experiment and makes it available as a fast random wine generator."
        ),
        "items": [
            "Original model work lives in the linked this-wine-does-not-exist repository",
            "The production app is this smaller wine-flask repository",
            "Generated descriptions are stored in SQLite",
            "Generated bottle labels are stored in MinIO",
        ],
    },
}
SITEMAP_PATHS = ["/", *SEO_PAGES.keys()]


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
        display_names = {
            WineCategory.PINOT_GRIS_GRIGIO: "Pinot Gris/Grigio",
            WineCategory.ROSE: "Rosé",
            WineCategory.SYRAH_SHIRAZ: "Syrah/Shiraz",
        }
        return display_names.get(self, self.name.replace("_", " ").title())


class Settings(BaseModel):
    minio_endpoint: str
    minio_access_key: str
    minio_secret_key: str
    # Analytics - Umami self-hosted on clifford
    umami_website_id: str = ""
    umami_script_src: str = ""
    umami_domains: str = ""
    umami_tag: str = "prod"
    umami_enabled: bool = False

    class Config:
        env_file = ".env"


settings = Settings(
    minio_endpoint=os.environ["MINIO_ENDPOINT"],
    minio_access_key=os.environ["MINIO_ACCESS_KEY"],
    minio_secret_key=os.environ["MINIO_SECRET_KEY"],
    umami_website_id=os.environ.get("UMAMI_WEBSITE_ID", ""),
    umami_script_src=os.environ.get("UMAMI_SCRIPT_SRC", ""),
    umami_domains=os.environ.get("UMAMI_DOMAINS", ""),
    umami_tag=os.environ.get("UMAMI_TAG", "prod"),
    umami_enabled=os.environ.get("UMAMI_ENABLED", "false").lower() in ("true", "1", "yes"),
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
    load_bottle_list()


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


def get_umami_context() -> dict:
    """Return all Umami analytics context variables for templates.

    Follows the organizational standard from ~/git/me/mytech/operations/umami.md
    """
    return {
        "umami_enabled": settings.umami_enabled,
        "umami_script_url": settings.umami_script_src,
        "umami_website_id": settings.umami_website_id,
        "umami_domains": settings.umami_domains,
    }


def get_seo_context(
    path: str,
    title: str = DEFAULT_TITLE,
    description: str = DEFAULT_DESCRIPTION,
) -> dict:
    canonical_url = f"{SITE_URL}{path}"
    return {
        "page_title": title,
        "page_description": description,
        "canonical_url": canonical_url,
        "site_url": SITE_URL,
        "og_image": f"{SITE_URL}/image",
        "current_year": date.today().year,
    }


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


def load_bottle_list() -> None:
    global BOTTLE_LIST
    BOTTLE_LIST = get_bottle_list()
    LOG.info(f"Loaded {len(BOTTLE_LIST)} wine bottle labels")


def sample_label_from_minio() -> BottleInfo:
    if not BOTTLE_LIST:
        load_bottle_list()
    return random.choice(BOTTLE_LIST)


@app.head("/")
@app.head("/wine")
def head_main():
    return Response(status_code=status.HTTP_200_OK)


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


@app.get("/robots.txt", include_in_schema=False)
def robots_txt():
    body = f"User-agent: *\nAllow: /\nSitemap: {SITE_URL}/sitemap.xml\n"
    return Response(content=body, media_type="text/plain")


@app.get("/sitemap.xml", include_in_schema=False)
def sitemap_xml():
    urls = "\n".join(
        f"  <url><loc>{SITE_URL}{path}</loc><changefreq>weekly</changefreq><priority>0.8</priority></url>"
        for path in SITEMAP_PATHS
    )
    body = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{urls}
</urlset>
"""
    return Response(content=body, media_type="application/xml")


@app.get("/ai-wine-generator", response_class=HTMLResponse)
@app.get("/fake-wine-name-generator", response_class=HTMLResponse)
@app.get("/ai-wine-label-generator", response_class=HTMLResponse)
@app.get("/wine-tasting-note-generator", response_class=HTMLResponse)
@app.get("/about", response_class=HTMLResponse)
def seo_page(request: Request):
    page = SEO_PAGES[request.url.path]
    return templates.TemplateResponse(
        "page.html",
        {
            "request": request,
            "page": page,
            **get_seo_context(
                request.url.path,
                title=str(page["title"]),
                description=str(page["description"]),
            ),
            **get_umami_context(),
        },
    )


@app.get("/", response_class=HTMLResponse)
@app.get("/wine", response_class=HTMLResponse)
def main(request: Request):
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
            **get_seo_context("/"),
            **get_umami_context(),
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
