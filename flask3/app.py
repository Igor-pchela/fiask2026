from flask import (
    Flask,
    render_template,
    redirect,
    url_for,
    request,
    flash
)
from flask_login import (
    LoginManager,
    UserMixin,
    login_user,
    login_required,
    logout_user,
    current_user
)
from werkzeug.security import generate_password_hash, check_password_hash
from forms import RegistrationForm, LoginForm
from utils import load_json, save_json
from datetime import datetime
import os
from pathlib import Path

app = Flask(__name__)
app.config["SECRET_KEY"] = os.urandom(256)

# Создаём папку data при запуске
DATA_FOLDER = Path(__file__).parent / "data"
DATA_FOLDER.mkdir(parents=True, exist_ok=True)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = "login"
login_manager.login_message = "Пожалуйста, авторизуйтесь для доступа к этой странице."


class User(UserMixin):
    def __init__(self, id, username, password_hash, registered_at, last_login):
        self.id = id
        self.username = username
        self.password_hash = password_hash
        self.registered_at = registered_at
        self.last_login = last_login


@login_manager.user_loader
def load_user(user_id):
    users_dct = load_json("data", "users.json")
    user_dct = users_dct.get(str(user_id))
    if user_dct:
        return User(
            str(user_id),
            user_dct['username'],
            user_dct['password_hash'],
            user_dct.get('registered_at', ''),
            user_dct.get('last_login', '')
        )
    return None


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    
    form = LoginForm()
    if request.method == "POST" and form.validate_on_submit():
        username = form.username.data
        password = form.password.data
        
        users_dct = load_json("data", "users.json")
        
        for key, user in users_dct.items():
            if user['username'] == username and check_password_hash(user['password_hash'], password):
                user['last_login'] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                save_json("data", "users.json", users_dct)
                
                user_obj = User(key, username, user['password_hash'], user['registered_at'], user['last_login'])
                login_user(user_obj)
                flash(f"Добро пожаловать, {username}!")
                
                next_page = request.args.get('next')
                if next_page:
                    return redirect(next_page)
                return redirect(url_for("index"))
        else:
            flash("Неверное имя пользователя или пароль.")
    
    return render_template("login.html", form=form)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Вы вышли из системы.")
    return redirect(url_for("index"))


@app.route("/register", methods=["GET", "POST"])
@login_required
def register():
    form = RegistrationForm()
    
    if request.method == "POST" and form.validate_on_submit():
        users_dct = load_json("data", "users.json")
        
        for user_data in users_dct.values():
            if user_data['username'] == form.username.data:
                flash("Пользователь с таким именем уже существует.")
                return render_template("register.html", form=form)
        
        new_id = str(len(users_dct) + 1)
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        new_user = {
            "username": form.username.data,
            "password_hash": generate_password_hash(form.password.data),
            "registered_at": current_time,
            "last_login": ""
        }
        
        users_dct[new_id] = new_user
        save_json("data", "users.json", users_dct)
        
        flash(f"Пользователь {form.username.data} зарегистрирован.")
        return redirect(url_for("users_list"))
    
    return render_template("register.html", form=form)


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/users")
@login_required
def users_list():
    users_dct = load_json("data", "users.json")
    
    users = []
    for user_id, user_data in users_dct.items():
        users.append({
            'id': user_id,
            'username': user_data['username'],
            'registered_at': user_data.get('registered_at', 'Не указана'),
            'last_login': user_data.get('last_login', 'Никогда')
        })
    
    return render_template("users_list.html", users=users)


if __name__ == "__main__":
    users_json_path = DATA_FOLDER / "users.json"
    
    if not users_json_path.exists() or users_json_path.stat().st_size == 0:
        users_dct = {}
        admin_password = "Admin123!"
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        admin_user = {
            "username": "admin",
            "password_hash": generate_password_hash(admin_password),
            "registered_at": current_time,
            "last_login": ""
        }
        users_dct["1"] = admin_user
        save_json("data", "users.json", users_dct)
        
        print("\n" + "="*50)
        print("АДМИНИСТРАТОР СОЗДАН")
        print("-"*50)
        print("Логин: admin")
        print("Пароль: Admin123!")
        print("="*50 + "\n")
    
    app.run(debug=True)