import pandas as pd
from numpy import random
from flask import Flask, render_template, url_for

app = Flask(__name__)

@app.route('/')
@app.route('/wine')
def main():
	#df = pd.read_csv('static/fake_wines_OLD.csv', sep='|')
	df = pd.read_excel('static/fake_names_descs_prices.xlsx')
	print(df.head())
	wine_ix = random.randint(0,len(df))
	wine_name = df.iloc[wine_ix,:]['name']
	wine_description = df.iloc[wine_ix,:]['description']
	wine_price = df.iloc[wine_ix,:]['price']
	wine_label_paths = os.listdir("static/labels_on_bottle/" )
	wine_image = random.choice(wine_label_paths)

	return render_template('index.html', 
                            w_name = wine_name,
                            w_description = wine_description,
							w_price = wine_price,
							w_image = wine_image)