import logging
from os import environ
import random
import sys

from firebase_admin import credentials, firestore, initialize_app
from flask import Flask, render_template

# Set paths
DATASET_DIR = "https://storage.googleapis.com/wine-flask/descriptions/"
IMAGE_DIR = "https://storage.googleapis.com/wine-flask/labels_on_bottle/"
FIRESTORE_COLLECTION = "gpt2-xl-outputs"

# Initialize logger
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
LOG = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Initialize Firestore client
firestore_creds = credentials.Certificate(environ['GOOGLE_APPLICATION_CREDENTIALS'])
firestore_app = initialize_app(firestore_creds)
store = firestore.client()

# Set paths
dataset_dir = "https://storage.googleapis.com/wine-flask/descriptions/"
image_dir = "https://storage.googleapis.com/wine-flask/labels_on_bottle_v2/"

def sample_from_firestore(return_random=True, doc_id=None):
    LOG.info("Starting firestore sample")
    if return_random == True:
        random_key = store.collection(FIRESTORE_COLLECTION).document().id
        result = store.collection(FIRESTORE_COLLECTION)\
            .where('id', '>=', random_key)\
            .limit(1)\
            .get()[0]
    else:
        result = store.collection(FIRESTORE_COLLECTION)\
            .where('id', '==', doc_id)\
            .limit(1)\
            .get()[0]   

    LOG.info(f"Returning firestore sample: {result}")
    return result.to_dict()


@app.route('/')
@app.route('/wine')
def main():
    LOG.info("Starting request")

    wine = sample_from_firestore(return_random=True)

    wine_name = wine['name']
    wine_category_1 = wine['category_1']
    wine_category_2 = wine['category_2']
    wine_origin = wine['origin']
    wine_description = wine['description']
    LOG.info(f"Returning description for: {wine_name}")

    # Sample a random wine bottle
    random_ix = random.sample(range(0, 622), k=1)[0]
    random_filename = f"wine_bottle_{random_ix:05d}.png"
    image_path = image_dir + random_filename
    LOG.info(f"Returning image path: {image_path}")

    return render_template(
        'index.html',
        w_name=wine_name,
        w_category_1 = wine_category_1,
        w_category_2 = wine_category_2,
        w_origin = wine_origin,
        w_description=wine_description,
        w_image=image_path
    )
