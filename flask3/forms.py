import string
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField
from wtforms.validators import DataRequired, Length, ValidationError, EqualTo


class LoginForm(FlaskForm):
    """Форма авторизации"""
    username = StringField('Имя пользователя', validators=[DataRequired()])
    password = PasswordField('Пароль', validators=[DataRequired()])
    submit = SubmitField('Войти')


class RegistrationForm(FlaskForm):
    """Форма регистрации нового пользователя"""
    
    def validate_password(self, field):
        """Валидация пароля: сложные требования к паролю"""
        password = field.data
        
        if len(password) < 8:
            raise ValidationError("Пароль должен быть длиной не менее 8 символов.")
        
        if not any(c.isdigit() for c in password):
            raise ValidationError("Пароль должен содержать хотя бы одну цифру.")
        
        if not any(c.islower() for c in password):
            raise ValidationError("Пароль должен содержать хотя бы одну строчную латинскую букву.")
        
        if not any(c.isupper() for c in password):
            raise ValidationError("Пароль должен содержать хотя бы одну заглавную латинскую букву.")
        
        if not any(c in string.punctuation for c in password):
            raise ValidationError("Пароль должен содержать хотя бы один специальный символ.")
    
    def validate_username(self, field):
        """Валидация имени пользователя"""
        username = field.data
        
        # Проверка на запрещённые имена
        forbidden_names = ["admin", "root", "superuser", "director", "chief", "boss", "administrator"]
        if username.lower() in forbidden_names:
            raise ValidationError("Это имя пользователя зарезервировано системой.")
        
        # Проверка на допустимые символы
        allowed_chars = set(string.ascii_lowercase + string.digits + "_")
        if not set(username.lower()) <= allowed_chars:
            raise ValidationError("Имя пользователя может содержать только латинские буквы, цифры и символ подчёркивания.")
        
        # Проверка длины
        if len(username) < 3:
            raise ValidationError("Имя пользователя должно содержать не менее 3 символов.")
    
    username = StringField(
        "Имя пользователя", 
        validators=[
            DataRequired(message="Имя пользователя обязательно."), 
            Length(min=3, max=25, message="Имя пользователя должно быть длиной от 3 до 25 символов."),
            validate_username
        ]
    )
    
    password = PasswordField(
        "Пароль", 
        validators=[
            DataRequired(message="Пароль обязателен."),
            validate_password
        ]
    )
    
    confirm = PasswordField(
        "Подтверждение пароля",
        validators=[
            DataRequired(message="Подтверждение пароля обязательно."),
            EqualTo("password", message="Пароли должны совпадать.")
        ]
    )
    
    submit = SubmitField("Зарегистрировать пользователя")