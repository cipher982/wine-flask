import logging
from os import listdir, path
import random

from flask import Flask, render_template
import pandas as pd

# Initialize Flask app
app = Flask(__name__)

# Set paths
dataset_dir = "./static/"
image_dir = "https://storage.googleapis.com/wine-flask/labels_on_bottle/"

@app.route('/')
@app.route('/wine')
def main():
	logging.info("Starting request in main()")
	dataset_path = path.join(dataset_dir, "fake_name_desc_price.pkl")
	dataset = pd.read_pickle(dataset_path)
	wine_ix = random.randint(0,len(dataset))
	wine_name = dataset.iloc[wine_ix,:]['name']
	wine_description = dataset.iloc[wine_ix,:]['description']
	wine_price = dataset.iloc[wine_ix,:]['price']

	# Sample a random wine bottle
	random_ix = random.sample(range(0,622), k=1)[0]
	random_filename = f"wine_bottle_{random_ix:05d}.png"
	logging.info(f"Sampled random wine {random_filename}")

	# Combine with full path
	image_path = path.join(image_dir, random_filename)
	logging.info(f"Returning image path {image_path}")

	return render_template(
		'index.html',
		w_name = wine_name,
        w_description = wine_description,
		w_price = wine_price,
		w_image = image_path
	)