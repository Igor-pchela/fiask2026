import sys
import os

# Добавляем текущую директорию в путь поиска модулей
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from flask import Flask, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, current_user, login_required
from datetime import datetime
import os

from extensions import db, login_manager
from models import User, Post
from forms import LoginForm, RegistrationForm, PostForm

app = Flask(__name__)
app.config["SECRET_KEY"] = os.urandom(24)
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///" + os.path.join(current_dir, "blog.db")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Инициализация расширений
db.init_app(app)
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# Маршруты для авторизации
@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(username=form.username.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash("Регистрация прошла успешно! Теперь вы можете войти.", "success")
        return redirect(url_for("login"))
    
    return render_template("register.html", form=form)


@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        return redirect(url_for("index"))
    
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            flash(f"Добро пожаловать, {user.username}!", "success")
            next_page = request.args.get("next")
            return redirect(next_page) if next_page else redirect(url_for("index"))
        else:
            flash("Неверное имя пользователя или пароль", "danger")
    
    return render_template("login.html", form=form)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("Вы вышли из системы", "info")
    return redirect(url_for("index"))


# Основные маршруты
@app.route("/")
def index():
    # Для авторизованных пользователей показываем все посты
    if current_user.is_authenticated:
        posts = Post.query.order_by(Post.created_at.desc()).all()
    else:
        # Для анонимных пользователей показываем только публичные посты
        posts = Post.query.filter_by(is_private=False).order_by(Post.created_at.desc()).all()
    
    return render_template("index.html", posts=posts)


@app.route("/post/<int:post_id>")
def view_post(post_id):
    post = Post.query.get_or_404(post_id)
    
    # Проверяем права доступа к приватному посту
    if post.is_private and not current_user.is_authenticated:
        flash("Это приватная запись. Пожалуйста, авторизуйтесь для просмотра.", "warning")
        return redirect(url_for("login"))
    
    return render_template("post_detail.html", post=post)


@app.route("/post/new", methods=["GET", "POST"])
@login_required
def create_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(
            title=form.title.data,
            content=form.content.data,
            is_private=form.is_private.data,
            user_id=current_user.id
        )
        db.session.add(post)
        db.session.commit()
        flash("Запись успешно создана!", "success")
        return redirect(url_for("view_post", post_id=post.id))
    
    return render_template("post_form.html", form=form, title="Создать запись")


@app.route("/post/<int:post_id>/edit", methods=["GET", "POST"])
@login_required
def edit_post(post_id):
    post = Post.query.get_or_404(post_id)
    
    # Проверяем, что пользователь является автором поста
    if post.user_id != current_user.id:
        flash("Вы можете редактировать только свои записи", "danger")
        return redirect(url_for("index"))
    
    form = PostForm(obj=post)
    if form.validate_on_submit():
        post.title = form.title.data
        post.content = form.content.data
        post.is_private = form.is_private.data
        post.updated_at = datetime.utcnow()
        db.session.commit()
        flash("Запись успешно обновлена!", "success")
        return redirect(url_for("view_post", post_id=post.id))
    
    return render_template("post_form.html", form=form, title="Редактировать запись")


@app.route("/post/<int:post_id>/delete", methods=["POST"])
@login_required
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    
    if post.user_id != current_user.id:
        flash("Вы можете удалять только свои записи", "danger")
        return redirect(url_for("index"))
    
    db.session.delete(post)
    db.session.commit()
    flash("Запись успешно удалена!", "success")
    return redirect(url_for("index"))


@app.route("/my-posts")
@login_required
def my_posts():
    posts = Post.query.filter_by(user_id=current_user.id).order_by(Post.created_at.desc()).all()
    return render_template("my_posts.html", posts=posts)


if __name__ == "__main__":
    with app.app_context():
        db.create_all()
    app.run(debug=True)