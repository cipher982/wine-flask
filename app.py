import random
import pandas as pd
from flask import Flask, render_template, url_for

app = Flask(__name__)

@app.route('/')
@app.route('/wine')
def main():
	df = pd.read_csv('static/fake_wines.csv', sep='|')
	wine_ix = random.randint(0,len(df))
	wine_name = df.iloc[wine_ix,:]['name']
	wine_description = df.iloc[wine_ix,:]['description']
	return render_template('index.html', 
                            w_name = wine_name,
                            w_description = wine_description)