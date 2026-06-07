from flask_wtf import FlaskForm
from flask_wtf.file import FileField  # FileAllowed больше не импортируем
from wtforms import StringField, TextAreaField, SelectField, BooleanField, DateField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, ValidationError
from datetime import date

class RegistrationForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired(), Length(min=3, max=64)])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=6)])
    submit = SubmitField('Зарегистрироваться')

class LoginForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')

class TaskForm(FlaskForm):
    title = StringField('Название', validators=[DataRequired(), Length(max=200)])
    description = TextAreaField('Описание', validators=[DataRequired()])
    priority = SelectField('Приоритет', choices=[('high', 'Высокий'), ('medium', 'Средний'), ('low', 'Низкий')])
    deadline = DateField('Дедлайн', validators=[DataRequired()], format='%Y-%m-%d')
    is_public = BooleanField('Публичная задача', default=True)
    file = FileField('Прикрепить файл')  # Убран валидатор FileAllowed
    submit = SubmitField('Сохранить')

    def validate_deadline(self, field):
        if field.data < date.today():
            raise ValidationError('Дедлайн не может быть в прошлом.')

class CommentForm(FlaskForm):
    content = TextAreaField('Комментарий', validators=[DataRequired()])
    file = FileField('Прикрепить файл')  # Убран валидатор
    submit = SubmitField('Добавить комментарий')

class StatusForm(FlaskForm):
    status = SelectField('Статус', choices=[
        ('new', 'Новый'),
        ('in_progress', 'В разработке'),
        ('done', 'Готово'),
        ('archived', 'В архив')
    ])
    submit = SubmitField('Изменить статус')