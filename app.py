from flask import Flask, render_template, request, send_from_directory, make_response
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import func
from datetime import datetime
from sqlalchemy import text
from collections import Counter
import os
from dotenv import load_dotenv

app = Flask(__name__)

# Load .env file security
load_dotenv()

# Get the environment variables
DB_USER = os.getenv('DB_USER')
DB_PASSWORD = os.getenv('DB_PASSWORD')
DB_HOST = os.getenv('DB_HOST')
DB_DATABASE = os.getenv('DB_DATABASE')

# Change the database URI to PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = f'postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}/{DB_DATABASE}'


# Optional: Silence the deprecation warning
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Presenca(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.String(255))
    wb_interval = db.Column(db.String(50))
    horario = db.Column(db.DateTime)

@app.route('/<path:subpath>/static/<path:filename>')
def serve_static(subpath, filename):
    root_dir = os.path.dirname(os.path.abspath(__file__))
    return send_from_directory(os.path.join(root_dir, subpath, 'static'), filename)

@app.route('/static/<path:filename>')
def custom_static(filename):
    cache_timeout = 60*60*24*365  # One year
    response = make_response(send_from_directory(os.path.join(app.root_path, 'static'), filename))
    response.headers.add('Cache-Control', 'public,max-age={}'.format(cache_timeout))
    return response

def get_wb_interval_from_path(path):
    if path == 'lab_manha':
        return 'Lab Manhã'
    elif path == 'vales_manha':
        return 'Vales Manhã'
    elif path == 'lab_noite':
        return 'Lab Noite'
    elif path == 'vales_noite':
        return 'Vales Noite'
    else:
        return path

@app.route('/')
def index():
    # Obtenha os usuários mais participativos
    usuarios_query = db.session.query(
        Presenca.usuario_id,
        func.count().label('total'),
        func.array_agg(Presenca.wb_interval).label('intervalos')
    ).group_by(Presenca.usuario_id).order_by(func.count().desc()).all()

    # Conta as ocorrências de cada intervalo de WB
    usuarios = []
    for usuario in usuarios_query:
        intervalos = Counter(usuario[2])
        intervalos_list = [{'wb': wb, 'count': count} for wb, count in intervalos.items()]
        usuarios.append((usuario[0], "Todas as datas", usuario[1], intervalos_list))

    return render_template('index.html', usuarios=usuarios)

@app.route('/presencas/<intervalo>')
def presencas(intervalo):
    wb_interval = get_wb_interval_from_path(intervalo)

    usuarios = db.session.query(
        Presenca.usuario_id,
        func.count().label('total'),
        Presenca.wb_interval
    ).filter_by(wb_interval=wb_interval).group_by(Presenca.usuario_id, Presenca.wb_interval).order_by(func.count().desc()).all()

    return render_template('presencas.html', intervalo=wb_interval, usuarios=usuarios)

def obter_lista_de_datas_do_banco_de_dados():
    datas = db.session.query(func.date(Presenca.horario)).distinct().order_by(func.date(Presenca.horario)).all()
    return [data[0].strftime('%d-%m-%Y') for data in datas]

@ app.route('/presencas/consolidado')
def consolidado():
    # Adiciona a lógica para filtrar por datas
    selected_data = request.args.get('data')
    if selected_data:
        # Modifica a query para filtrar somente pela data
        usuarios_query = db.session.query(
            Presenca.usuario_id,
            func.date(Presenca.horario),
            func.count().label('total'),
            func.array_agg(Presenca.wb_interval).label('intervalos')
        ).filter(func.date(Presenca.horario) == datetime.strptime(selected_data, '%d-%m-%Y').date()).group_by(Presenca.usuario_id, func.date(Presenca.horario)).order_by(func.count().desc()).all()
    else:
        usuarios_query = db.session.query(
            Presenca.usuario_id,
            func.count().label('total'),
            func.array_agg(Presenca.wb_interval).label('intervalos')
        ).group_by(Presenca.usuario_id).order_by(func.count().desc()).all()

    # Conta as ocorrências de cada intervalo de WB
    usuarios = []
    for usuario in usuarios_query:
        if selected_data:
            intervalos = Counter(usuario[3])
            intervalos_list = [{'wb': wb, 'count': count} for wb, count in intervalos.items()]
            usuarios.append((usuario[0], usuario[1], usuario[2], intervalos_list))
        else:
            intervalos = Counter(usuario[2])
            intervalos_list = [{'wb': wb, 'count': count} for wb, count in intervalos.items()]
            usuarios.append((usuario[0], "Todas as datas", usuario[1], intervalos_list))

    # Adicione o retorno da renderização do template
    return render_template('consolidado.html', usuarios=usuarios, datas=obter_lista_de_datas_do_banco_de_dados(), selectedData=selected_data)



if __name__ == "__main__":
    from waitress import serve
    serve(app, host="0.0.0.0", port=8080)
