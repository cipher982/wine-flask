import logging
from os import environ
import random
import sys

from firebase_admin import credentials, firestore, initialize_app
from flask import Flask, render_template
from google.cloud import storage
from google.oauth2 import service_account
from retry import retry

# Set constants
GCLOUD_BUCKET = 'wine-flask'
LABELS_BLOB = "labels_on_bottle_v2/bottle_cat_"
DATASET_DIR = f"https://storage.googleapis.com/{GCLOUD_BUCKET}/descriptions/"
IMAGE_DIR = f"https://storage.googleapis.com/{GCLOUD_BUCKET}/"
FIRESTORE_COLLECTION = "gpt2-xl-outputs"
CAT_2_DICT = {
    1:"Bordeaux Red Blends",
    2:"Cabernet Sauvignon",
    3:"Chardonnay",
    4:"Merlot",
    5:"Other Red Blends",
    6:"Other White Blends",
    7:"Pinot Gris/Grigio",
    8:"Pinot Noir",
    9:"Rhone Red Blends",
    10:"Riesling",
    11:"Rosé",
    12:"Sangiovese",
    13:"Sauvignon Blanc",
    14:"Syrah/Shiraz",
    15:"Zinfandel"
}


# Initialize logger
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
LOG = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Initialize Firestore client
firestore_creds = credentials.Certificate(environ['GOOGLE_APPLICATION_CREDENTIALS'])
firestore_app = initialize_app(firestore_creds)
store = firestore.client()

# Initialize google.cloud client
gcloud_creds = service_account.Credentials.from_service_account_file(environ['GOOGLE_APPLICATION_CREDENTIALS'])

# Create list of bottles from gcloud blob
storage_client = storage.Client(credentials=gcloud_creds)
blobs = storage_client.list_blobs(GCLOUD_BUCKET, prefix=LABELS_BLOB, delimiter=None)
blobs = [(int(i.name.split('cat_')[1].split('_')[0]), i.name) for i in blobs]


def sample_from_firestore(return_random=True, label_cat_2=None, doc_id=None):
    LOG.info("Starting firestore sample")
    if return_random == True:
        random_key = store.collection(FIRESTORE_COLLECTION).document().id
        result = store.collection(FIRESTORE_COLLECTION)\
            .where('category_2', '==', CAT_2_DICT[label_cat_2])\
            .where('id', '>=', random_key)\
            .limit(1)\
            .get()[0]
    else:
        result = store.collection(FIRESTORE_COLLECTION)\
            .where('category_2', '==', CAT_2_DICT[label_cat_2])\
            .limit(1)\
            .get()[0]   

    LOG.info(f"Returning firestore sample: {result}")
    return result.to_dict()

def sample_label_from_gcs():
    return random.choice(blobs)


@app.route('/')
@app.route('/wine')
@retry((Exception), tries=5, delay=0, backoff=0)
def main():
    LOG.info("Starting request")
    
    # Sample a random wine label
    label_cat_2, label_path = sample_label_from_gcs()
    image_path = IMAGE_DIR + label_path
    LOG.info(f"Returning image path: {image_path}")

    # Sample random description matching the label category
    wine_description = None
    while wine_description == None:
        wine = sample_from_firestore(return_random=True, label_cat_2=label_cat_2)
        wine_name = wine['name']
        wine_category_1 = wine['category_1']
        wine_category_2 = wine['category_2']
        wine_origin = wine['origin']
        wine_description = wine['description']
    LOG.info(f"Returning description for: {wine_name}")

    return render_template(
        'index.html',
        w_name=wine_name,
        w_category_1 = wine_category_1,
        w_category_2 = wine_category_2,
        w_origin = wine_origin,
        w_description=wine_description,
        w_image=image_path
    )
