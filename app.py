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


if __name__ == '__main__':
    app.run(debug=True)
