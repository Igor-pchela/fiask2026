from app import app
from extensions import db
from models import User, Post


def init_db():
    """Создание таблиц и добавление тестовых данных"""
    with app.app_context():
        # Создаем все таблицы
        db.create_all()
        
        # Проверяем, есть ли уже пользователи
        if User.query.count() == 0:
            # Создаем тестовых пользователей
            test_users = [
                ("alex", "pass123"),
                ("maria", "pass456"),
                ("john", "pass789"),
            ]
            
            created_users = []
            for username, password in test_users:
                user = User(username=username)
                user.set_password(password)
                db.session.add(user)
                created_users.append(user)
            
            db.session.commit()
            
            # Создаем тестовые посты
            posts_data = [
                ("Добро пожаловать в блог!", "Это публичный пост. Он виден всем пользователям, даже неавторизованным.", False, created_users[0]),
                ("Мои мысли о программировании", "Это приватный пост. Только авторизованные пользователи могут его видеть.", True, created_users[0]),
                ("Новости технологий", "Публичная новость о последних технологических достижениях.", False, created_users[1]),
                ("Личные заметки", "Это приватная заметка, доступная только после авторизации.", True, created_users[1]),
                ("Советы для начинающих", "Полезные советы для всех пользователей блога.", False, created_users[2]),
            ]
            
            for title, content, is_private, user in posts_data:
                post = Post(
                    title=title,
                    content=content,
                    is_private=is_private,
                    user_id=user.id
                )
                db.session.add(post)
            
            db.session.commit()
            
            print("=" * 50)
            print("База данных успешно инициализирована!")
            print("=" * 50)
            print("\n📝 Тестовые пользователи:")
            for user in created_users:
                print(f"  • Логин: {user.username}")
            print("\n🔑 Пароли для всех тестовых пользователей:")
            print("  • alex: pass123")
            print("  • maria: pass456")
            print("  • john: pass789")
            print("\n" + "=" * 50)
        else:
            print("База данных уже содержит данные")


if __name__ == "__main__":
    init_db()