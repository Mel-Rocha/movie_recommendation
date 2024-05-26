import psycopg2
from flask import Flask, redirect, url_for, render_template, request
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from flask_principal import Principal, Permission, RoleNeed, UserNeed, Identity, identity_loaded, identity_changed, \
    AnonymousIdentity

app = Flask(__name__)
app.secret_key = 'supersecretkey'

# Configurações do Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Configurações do Flask-Principal
principal = Principal(app)

# Definição de permissões
admin_permission = Permission(RoleNeed('admin'))
user_permission = Permission(RoleNeed('user'))

# Mock de usuários
users = {
    'admin': {'password': 'admin', 'roles': ['admin']},
    'user': {'password': 'user', 'roles': ['user']}
}


class User(UserMixin):
    def __init__(self, username):
        self.id = username
        self.roles = users[username]['roles']


@login_manager.user_loader
def load_user(user_id):
    if user_id in users:
        return User(user_id)
    return None


@identity_loaded.connect_via(app)
def on_identity_loaded(sender, identity):
    identity.user = current_user
    if hasattr(current_user, 'id'):
        identity.provides.add(UserNeed(current_user.id))
        for role in current_user.roles:
            identity.provides.add(RoleNeed(role))


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users and users[username]['password'] == password:
            user = User(username)
            login_user(user)
            identity_changed.send(app, identity=Identity(user.id))
            return redirect(url_for('index'))
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    identity_changed.send(app, identity=AnonymousIdentity())
    return redirect(url_for('login'))


@app.route('/')
@login_required
def index():
    return 'Hello, %s!' % current_user.id


@app.route('/admin')
@login_required
@admin_permission.require(http_exception=403)
def admin():
    return 'Hello, Admin!'


@app.route('/user')
@login_required
@user_permission.require(http_exception=403)
def user():
    return 'Hello, User!'


def buscar_filmes():
    try:
        connection = psycopg2.connect(
            user="postgres",
            password="root",
            host="localhost",
            port="5432",
            database="recomendacao_filmes"
        )

        cursor = connection.cursor()

        # Execute a query to fetch all movies
        cursor.execute("SELECT * FROM filmes;")
        filmes = cursor.fetchall()

        # Convert the list of tuples to a list of dictionaries
        filmes = [{'ID': f[0], 'Nome': f[1], 'Gênero': f[2], 'Tags': f[3]} for f in filmes]

        return filmes

    except (Exception, psycopg2.Error) as error:
        print("Error while connecting to PostgreSQL", error)
    finally:
        # closing database connection.
        if connection:
            cursor.close()
            connection.close()
            print("PostgreSQL connection is closed")


def calcular_similaridade(filme1, filme2):
    similaridade = 0
    similaridade += (filme1['Gênero'] == filme2['Gênero'])
    similaridade += len(set(filme1['Tags']).intersection(set(filme2['Tags'])))
    return similaridade


def recomendar_filmes(base_filme_nome):
    filmes = buscar_filmes()
    base_filme = next((f for f in filmes if f['Nome'] == base_filme_nome), None)
    recomendacoes = []

    if base_filme is None:
        return []

    for filme in filmes:
        if filme['Nome'] != base_filme_nome:
            similaridade = calcular_similaridade(base_filme, filme)
            recomendacoes.append((filme['Nome'], similaridade))

    recomendacoes.sort(key=lambda x: x[1], reverse=True)

    return [rec[0] for rec in recomendacoes[:3]]


@app.route('/recomendar/<filme_assistido>')
def recomendar(filme_assistido):
    filmes_recomendados = recomendar_filmes(filme_assistido)
    return {
        "Filmes recomendados baseados em seu interesse por '{}':".format(filme_assistido): filmes_recomendados
    }


if __name__ == '__main__':
    app.run(debug=True)
