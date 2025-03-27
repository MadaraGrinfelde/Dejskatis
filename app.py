from flask import Flask, render_template, request, jsonify
from peewee import *
import matplotlib
import matplotlib.pyplot as plt
import csv
import plotly.express as px
import pandas as pd


matplotlib.use('Agg')

app = Flask(__name__)

db = SqliteDatabase('rezultati.db')

class Kolektivs(Model):
    id = AutoField(primary_key=True)
    uzstasanas_nr = IntegerField()
    nosaukums = CharField()
    vaditajs = CharField()
    kvalitates_grupa = CharField()
    gala_vert_punkti = FloatField()
    piezimes_lemums = CharField()

    class Meta:
        database = db

db.connect()
db.create_tables([Kolektivs])

@app.route('/', methods=['GET'])
def display_results():
    filters = {
        'nosaukums': request.args.get('nosaukums'),
        'kvalitates_grupa': request.args.getlist('kvalitates_grupa'),
        'vaditajs': request.args.getlist('vaditajs'),
        'piezimes_lemums': request.args.getlist('piezimes_lemums'),
        'gala_vert_min': request.args.get('gala_vert_min', '0'),
        'gala_vert_max': request.args.get('gala_vert_max', '65')
    }

    query = Kolektivs.select()

    if filters['nosaukums']:
        query = query.where(Kolektivs.nosaukums.contains(filters['nosaukums']))
    if filters['kvalitates_grupa']:
        query = query.where(Kolektivs.kvalitates_grupa.in_(filters['kvalitates_grupa']))
    if filters['vaditajs']:
        query = query.where(Kolektivs.vaditajs.in_(filters['vaditajs']))
    if filters['piezimes_lemums']:
        query = query.where(Kolektivs.piezimes_lemums.in_(filters['piezimes_lemums']))
    if filters['gala_vert_min'] and filters['gala_vert_max']:
        query = query.where(Kolektivs.gala_vert_punkti.between(float(filters['gala_vert_min']), float(filters['gala_vert_max'])))

    kvalitates_grupas = [row.kvalitates_grupa for row in Kolektivs.select(Kolektivs.kvalitates_grupa).distinct()]
    vaditaji = [row.vaditajs for row in Kolektivs.select(Kolektivs.vaditajs).distinct()]
    piezimes = [row.piezimes_lemums for row in Kolektivs.select(Kolektivs.piezimes_lemums).distinct()]

    return render_template('results.html', kolektivs=query, filters=filters,
                           kvalitates_grupas=kvalitates_grupas,
                           vaditaji=vaditaji, piezimes=piezimes)

@app.route('/dataimport', methods=['GET', 'POST'])
def dataimport():
    if request.method == 'POST':
        uploaded_file = request.files.get('csv_file')
        if uploaded_file and uploaded_file.filename.endswith('.csv'):
            file_content = uploaded_file.stream.read().decode('utf-8')
            rows = csv.DictReader(file_content.splitlines())
            
            for row in rows:
                Kolektivs.create(
                    uzstasanas_nr=row["Uzstāšanās Nr."],
                    nosaukums=row["Kolektīva nosaukums"],
                    vaditajs=row["Vadītājs"],
                    kvalitates_grupa=row["Kvalitātes grupa"],
                    gala_vert_punkti=float(row["Gala vērtējums (punkti)"]),
                    piezimes_lemums=row["Piezīmes, lēmums"]
                )

    return render_template('dataimport.html')

@app.route('/chart')
def chart():
    db.connect()
    df = pd.DataFrame(list(Kolektivs.select().dicts()))
    db.close()
    
    fig = px.bar(
        df, 
        x='nosaukums', 
        y='gala_vert_punkti', 
        color='kvalitates_grupa', 
        title="Rezultāti pēc kvalitātes grupas"
    )
    fig.update_layout(
        width=1200,  
        height=1200  
    )
    
    chart_html = fig.to_html(full_html=False)
    return render_template('chart1.html', chart=chart_html)

import matplotlib.pyplot as plt
import mpld3

@app.route('/chart2')
def chart2():
    db.connect()
    df = pd.DataFrame(list(Kolektivs.select().dicts()))
    db.close()
    

    fig, ax = plt.subplots(figsize=(12, 8)) 
    plt.subplots_adjust(bottom=0.3, top=0.9)
    bars = ax.bar(df['nosaukums'], df['gala_vert_punkti'], color='skyblue')
    ax.set_title('Rezultāti pēc kvalitātes grupas', fontsize=16)
    ax.set_xlabel('nosaukums', fontsize=7)
    ax.set_ylabel('Rezultāti', fontsize=12)
    ax.tick_params(axis='x', rotation=0)
    fig.tight_layout()

    tooltip = mpld3.plugins.PointLabelTooltip(bars, labels=df['gala_vert_punkti'].astype(str).tolist())
    mpld3.plugins.connect(fig, tooltip)

    chart_html = mpld3.fig_to_html(fig)
    plt.close(fig)

    return render_template('chart2.html', chart_html=chart_html)

@app.route('/charts', methods=['POST'])
def charts():
    filters = request.get_json()
    query = Kolektivs.select()

    if filters['kvalitates_grupa']:
        query = query.where(Kolektivs.kvalitates_grupa.in_(filters['kvalitates_grupa']))
    if filters['vaditajs']:
        query = query.where(Kolektivs.vaditajs.in_(filters['vaditajs']))
    if filters['piezimes_lemums']:
        query = query.where(Kolektivs.piezimes_lemums.in_(filters['piezimes_lemums']))
    if filters['gala_vert_min'] and filters['gala_vert_max']:
        query = query.where(Kolektivs.gala_vert_punkti.between(float(filters['gala_vert_min']), float(filters['gala_vert_max'])))

    kval_grupa_count = {}
    piezimes_count = {}

    for row in query:
        kval_grupa_count[row.kvalitates_grupa] = kval_grupa_count.get(row.kvalitates_grupa, 0) + 1
        piezimes_count[row.piezimes_lemums] = piezimes_count.get(row.piezimes_lemums, 0) + 1

    return jsonify({
        "kval_grupa_count": kval_grupa_count,
        "piezimes_count": piezimes_count
    })

if __name__ == '__main__':
    app.run(debug=True)