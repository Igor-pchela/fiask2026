from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, BooleanField, SubmitField, PasswordField
from wtforms.validators import DataRequired, Length, EqualTo, ValidationError
from models import User


class LoginForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')


class RegistrationForm(FlaskForm):
    username = StringField('Имя пользователя', validators=[DataRequired(), Length(min=3, max=80)])
    password = PasswordField('Пароль', validators=[DataRequired(), Length(min=6)])
    confirm_password = PasswordField('Подтвердите пароль', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Зарегистрироваться')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user:
            raise ValidationError('Это имя пользователя уже занято. Выберите другое.')


class PostForm(FlaskForm):
    title = StringField('Заголовок', validators=[DataRequired(), Length(min=3, max=200)])
    content = TextAreaField('Содержание', validators=[DataRequired(), Length(min=10)])
    is_private = BooleanField('Сделать запись приватной (видна только авторизованным пользователям)')
    submit = SubmitField('Сохранить')