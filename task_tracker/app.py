import os
from datetime import datetime, timedelta, date
from flask import Flask, render_template, redirect, url_for, request, flash, abort, send_from_directory
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from sqlalchemy import func, case

from config import Config
from models import db, User, Task, Comment
from forms import RegistrationForm, LoginForm, TaskForm, CommentForm, StatusForm
from utils import save_file

app = Flask(__name__)
app.config.from_object(Config)
db.init_app(app)
login_manager = LoginManager(app)
login_manager.login_view = 'login'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# ---------- Вспомогательные функции ----------
def apply_filters_and_sort(query, filters):
    """Применяет фильтры и сортировку к запросу задач."""
    status = filters.get('status')
    if status and status != 'all':
        query = query.filter(Task.status == status)
    priority = filters.get('priority')
    if priority and priority != 'all':
        query = query.filter(Task.priority == priority)
    deadline_from = filters.get('deadline_from')
    if deadline_from:
        query = query.filter(Task.deadline >= deadline_from)
    deadline_to = filters.get('deadline_to')
    if deadline_to:
        query = query.filter(Task.deadline <= deadline_to)
    created_from = filters.get('created_from')
    if created_from:
        query = query.filter(Task.created_at >= datetime.combine(created_from, datetime.min.time()))
    created_to = filters.get('created_to')
    if created_to:
        query = query.filter(Task.created_at <= datetime.combine(created_to, datetime.max.time()))

    sort_by = filters.get('sort', 'created_desc')
    if sort_by == 'status':
        status_order = case(
            (Task.status == 'new', 1),
            (Task.status == 'in_progress', 2),
            (Task.status == 'done', 3),
            (Task.status == 'archived', 4),
            else_=5
        )
        query = query.order_by(status_order)
    elif sort_by == 'created_asc':
        query = query.order_by(Task.created_at.asc())
    elif sort_by == 'created_desc':
        query = query.order_by(Task.created_at.desc())
    elif sort_by == 'deadline_asc':
        query = query.order_by(Task.deadline.asc())
    elif sort_by == 'deadline_desc':
        query = query.order_by(Task.deadline.desc())
    elif sort_by == 'priority':
        priority_order = case(
            (Task.priority == 'high', 1),
            (Task.priority == 'medium', 2),
            (Task.priority == 'low', 3),
            else_=4
        )
        query = query.order_by(priority_order)
    return query

def get_accessible_tasks(user):
    """Возвращает Query объектов Task, доступных пользователю (свои + публичные)."""
    if user.is_admin():
        return Task.query
    return Task.query.filter(
        (Task.author_id == user.id) | (Task.is_public == True)
    )

# ---------- Аутентификация ----------
@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('tasks'))
    form = RegistrationForm()
    if form.validate_on_submit():
        if User.query.filter_by(username=form.username.data).first():
            flash('Пользователь с таким именем уже существует.', 'danger')
            return redirect(url_for('register'))
        user = User(username=form.username.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        flash('Регистрация успешна! Войдите.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html', form=form)

@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('tasks'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('tasks'))
        flash('Неверное имя пользователя или пароль.', 'danger')
    return render_template('login.html', form=form)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# ---------- Список задач (мои / публичные) ----------
@app.route('/tasks')
@login_required
def tasks():
    show = request.args.get('show', 'my')
    filters = {
        'status': request.args.get('status'),
        'priority': request.args.get('priority'),
        'deadline_from': request.args.get('deadline_from'),
        'deadline_to': request.args.get('deadline_to'),
        'created_from': request.args.get('created_from'),
        'created_to': request.args.get('created_to'),
        'sort': request.args.get('sort', 'created_desc')
    }
    for key in ['deadline_from', 'deadline_to', 'created_from', 'created_to']:
        if filters.get(key):
            try:
                filters[key] = datetime.strptime(filters[key], '%Y-%m-%d').date()
            except:
                filters[key] = None

    if show == 'my':
        query = Task.query.filter_by(author_id=current_user.id)
    else:
        query = Task.query.filter(Task.is_public == True)

    query = apply_filters_and_sort(query, filters)
    page = request.args.get('page', 1, type=int)
    pagination = query.paginate(page=page, per_page=10, error_out=False)
    tasks_list = pagination.items
    return render_template('tasks.html', tasks=tasks_list, pagination=pagination, show=show, filters=filters)

# ---------- Создание задачи ----------
@app.route('/task/create', methods=['GET', 'POST'])
@login_required
def create_task():
    form = TaskForm()
    if form.validate_on_submit():
        file_path = save_file(form.file.data, 'tasks')
        task = Task(
            title=form.title.data,
            description=form.description.data,
            priority=form.priority.data,
            deadline=form.deadline.data,
            is_public=form.is_public.data,
            file_path=file_path,
            author_id=current_user.id
        )
        db.session.add(task)
        db.session.commit()
        flash('Задача создана!', 'success')
        return redirect(url_for('tasks'))
    return render_template('create_task.html', form=form)

# ---------- Просмотр задачи, комментарии, смена статуса ----------
@app.route('/task/<int:id>', methods=['GET', 'POST'])
@login_required
def view_task(id):
    task = Task.query.get_or_404(id)
    if not task.can_view(current_user):
        abort(403)

    comment_form = CommentForm()
    status_form = StatusForm()

    if status_form.validate_on_submit() and 'change_status' in request.form:
        new_status = status_form.status.data
        if new_status == 'archived' and not task.can_archive(current_user):
            flash('Только автор задачи может отправить её в архив.', 'danger')
            return redirect(url_for('view_task', id=task.id))
        task.status = new_status
        db.session.commit()
        flash('Статус обновлён.', 'success')
        return redirect(url_for('view_task', id=task.id))

    if comment_form.validate_on_submit() and 'add_comment' in request.form:
        file_path = save_file(comment_form.file.data, 'comments')
        comment = Comment(
            content=comment_form.content.data,
            file_path=file_path,
            user_id=current_user.id,
            task_id=task.id
        )
        db.session.add(comment)
        db.session.commit()
        flash('Комментарий добавлен.', 'success')
        return redirect(url_for('view_task', id=task.id))

    comments = task.comments.order_by(Comment.created_at.asc()).all()
    return render_template('task_detail.html', task=task, comments=comments,
                           comment_form=comment_form, status_form=status_form)

# ---------- Редактирование задачи ----------
@app.route('/task/<int:id>/edit', methods=['GET', 'POST'])
@login_required
def edit_task(id):
    task = Task.query.get_or_404(id)
    if not task.can_edit(current_user):
        abort(403)
    if task.status == 'archived':
        flash('Нельзя редактировать архивную задачу.', 'warning')
        return redirect(url_for('view_task', id=task.id))

    form = TaskForm(obj=task)
    if form.validate_on_submit():
        task.title = form.title.data
        task.description = form.description.data
        task.priority = form.priority.data
        task.deadline = form.deadline.data
        task.is_public = form.is_public.data
        if form.file.data:
            new_file = save_file(form.file.data, 'tasks')
            if new_file:
                task.file_path = new_file
        db.session.commit()
        flash('Задача обновлена.', 'success')
        return redirect(url_for('view_task', id=task.id))
    elif request.method == 'GET':
        form.deadline.data = task.deadline
    return render_template('edit_task.html', form=form, task=task)

# ---------- Отдельный маршрут для архивации ----------
@app.route('/task/<int:id>/archive', methods=['POST'])
@login_required
def archive_task(id):
    task = Task.query.get_or_404(id)
    if not task.can_archive(current_user):
        abort(403)
    if task.status != 'archived':
        task.status = 'archived'
        db.session.commit()
        flash('Задача перемещена в архив.', 'success')
    else:
        flash('Задача уже в архиве.', 'info')
    return redirect(url_for('view_task', id=task.id))

# ---------- Скачивание файлов ----------
@app.route('/download/task/<int:task_id>')
@login_required
def download_task_file(task_id):
    task = Task.query.get_or_404(task_id)
    if not task.can_view(current_user):
        abort(403)
    if not task.file_path:
        abort(404)
    directory = app.config['UPLOAD_FOLDER']
    return send_from_directory(directory, task.file_path, as_attachment=True)

@app.route('/download/comment/<int:comment_id>')
@login_required
def download_comment_file(comment_id):
    comment = Comment.query.get_or_404(comment_id)
    task = comment.task
    if not task.can_view(current_user):
        abort(403)
    if not comment.file_path:
        abort(404)
    directory = app.config['UPLOAD_FOLDER']
    return send_from_directory(directory, comment.file_path, as_attachment=True)

# ---------- Статистика ----------
@app.route('/statistics')
@login_required
def statistics():
    today = date.today()
    week_ago = today - timedelta(days=7)
    month_ago = today - timedelta(days=30)
    if current_user.is_admin():
        tasks_query = Task.query
    else:
        tasks_query = Task.query.filter_by(author_id=current_user.id)
    done_week = tasks_query.filter(Task.status == 'done', Task.created_at >= week_ago).count()
    done_month = tasks_query.filter(Task.status == 'done', Task.created_at >= month_ago).count()
    return render_template('statistics.html', done_week=done_week, done_month=done_month)

# ---------- Поиск ----------
@app.route('/search')
@login_required
def search():
    query_str = request.args.get('q', '').strip()
    if not query_str:
        return redirect(url_for('tasks'))
    accessible = get_accessible_tasks(current_user)
    results = accessible.filter(
        Task.title.ilike(f'%{query_str}%') | Task.description.ilike(f'%{query_str}%')
    ).order_by(Task.created_at.desc()).all()
    return render_template('search_results.html', query=query_str, results=results)

# ---------- Обработка ошибок ----------
@app.errorhandler(403)
def forbidden(e):
    flash('У вас нет доступа к этой странице. Пожалуйста, войдите в другой аккаунт.', 'warning')
    return redirect(url_for('login'))

@app.errorhandler(404)
def not_found(e):
    flash('Пожалуйста, войдите или зарегистрируйтесь.', 'warning')
    return redirect(url_for('login'))

# ---------- Инициализация БД и создание администратора ----------
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        if not User.query.first():
            admin = User(username='admin', role='admin')
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
    app.run(debug=True)