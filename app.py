import logging
from os import listdir
import random

from flask import Flask, render_template, url_for
import pandas as pd


app = Flask(__name__)

@app.route('/')
@app.route('/wine')
def main():
	logging.info("Starting request in main()")
	df = pd.read_excel('static/fake_names_descs_prices.xls')
	wine_ix = random.randint(0,len(df))
	wine_name = df.iloc[wine_ix,:]['name']
	wine_description = df.iloc[wine_ix,:]['description']
	wine_price = df.iloc[wine_ix,:]['price']

	# Sample a random wine bottle
	random_ix = random.sample(range(0,622), k=1)[0]
	random_filename = f"wine_bottle_{random_ix:05d}.png"
	logging.info(f"Sampled random wine {random_filename}")

	# Combine with full path
	image_dir = "https://storage.googleapis.com/wine-flask/labels_on_bottle/"
	image_path = f"{image_dir}{random_filename}"
	logging.info(f"Returning image path {image_path}")

	return render_template(
		'index.html',
		w_name = wine_name,
        w_description = wine_description,
		w_price = wine_price,
		w_image = image_path
	)