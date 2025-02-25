from flask import Flask, render_template
import pandas as pd
import json

app = Flask(__name__)

@app.route('/')
def index():

    df = pd.read_csv('candidatos_encontrados.csv')
    
    dados_json = df.to_dict(orient='records')
    
    return render_template('index.html', candidatos=dados_json)

if __name__ == '__main__':
    app.run(debug=True)