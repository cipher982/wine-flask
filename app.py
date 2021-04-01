import logging
from os import listdir
from pathlib import Path
import random
import sys

from flask import Flask, render_template
import pandas as pd
#import pickle5 as pickle

# Initialize logger
logging.basicConfig(stream=sys.stdout, level=logging.INFO)
LOG = logging.getLogger(__name__)

# Initialize Flask app
app = Flask(__name__)

# Set paths
dataset_dir = "https://storage.googleapis.com/wine-flask/descriptions/"
image_dir = "https://storage.googleapis.com/wine-flask/labels_on_bottle/"


@app.route('/')
@app.route('/wine')
def main():
    LOG.info("Starting request in main()")
    dataset_path = dataset_dir + "cleaned_gpt_descriptions_835.csv"
    dataset = pd.read_csv(dataset_path)
    wine_ix = random.randint(0, len(dataset))
    wine_name = dataset.iloc[wine_ix, :]['name']
    wine_category_1 = dataset.iloc[wine_ix, :]['category_1']
    wine_category_2 = dataset.iloc[wine_ix, :]['category_2']
    wine_origin = dataset.iloc[wine_ix, :]['origin']
    wine_description = dataset.iloc[wine_ix, :]['description']
    #wine_price = dataset.iloc[wine_ix, :]['price']

    # Sample a random wine bottle
    random_ix = random.sample(range(0, 622), k=1)[0]
    random_filename = f"wine_bottle_{random_ix:05d}.png"
    LOG.info(f"Sampled random wine {random_filename}")

    # Combine with full path
    image_path = Path(image_dir, random_filename)
    LOG.info(f"Returning image path {image_path}")

    return render_template(
        'index.html',
        w_name=wine_name,
        w_category_1 = wine_category_1,
        w_category_2 = wine_category_2,
        w_origin = wine_origin,
        w_description=wine_description,
        #w_price=wine_price,
        w_image=image_path
    )
