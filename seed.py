from app import create_app
from models import db, Role, User, Genre, Book, BookGenre, Cover
import os
import hashlib
import shutil


def add_user(login, password, last_name, first_name, middle_name, role):
    user = User.query.filter_by(login=login).first()
    if not user:
        user = User(
            login=login,
            last_name=last_name,
            first_name=first_name,
            middle_name=middle_name,
            role=role
        )
        user.set_password(password)
        db.session.add(user)


def add_genre(name):
    genre = Genre.query.filter_by(name=name).first()
    if not genre:
        genre = Genre(name=name)
        db.session.add(genre)
    return genre


def add_book(title, description, year, pages, publisher, author, genre_names, cover_file, app):
    book = Book.query.filter_by(title=title).first()
    if book:
        return book

    book = Book(
        title=title,
        description=description,
        year=year,
        pages=pages,
        publisher=publisher,
        author=author
    )

    for name in genre_names:
        genre = Genre.query.filter_by(name=name).first()
        if genre:
            book.genres_assoc.append(BookGenre(genre=genre))

    db.session.add(book)
    db.session.flush()

    src_path = os.path.join(app.static_folder, 'covers', cover_file)

    with open(src_path, 'rb') as f:
        file_data = f.read()

    md5_hash = hashlib.md5(file_data).hexdigest()
    ext = os.path.splitext(cover_file)[1]

    cover = Cover(
        filename='',
        mime_type='image/jpeg' if ext.lower() in ['.jpg', '.jpeg'] else 'image/png',
        md5_hash=md5_hash,
        book_id=book.id
    )

    db.session.add(cover)
    db.session.flush()

    cover.filename = f'{cover.id}{ext}'

    dst_path = os.path.join(app.static_folder, 'covers', cover.filename)
    shutil.copyfile(src_path, dst_path)

    db.session.commit()
    return book


def main():
    app = create_app()

    with app.app_context():
        admin_role = Role.query.filter_by(name='administrator').first()
        moderator_role = Role.query.filter_by(name='moderator').first()
        user_role = Role.query.filter_by(name='user').first()

        add_user('admin', '123321', 'Клевин', 'Администратор', None, admin_role)
        add_user('moder', '123321', 'Клевин', 'Модератор', None, moderator_role)
        add_user('klevin', '123321', 'Клевин', 'Александр', 'Ильич', user_role)

        add_genre('Роман')
        add_genre('Фантастика')
        add_genre('Детектив')
        add_genre('Научная литература')
        add_genre('История')

        db.session.commit()

        add_book(
            'Ведьмак: Перекрёсток воронов',
            'Описание будет добавлено позже.',
            2024,
            292,
            'SuperNowa',
            'Анджей Сапковский',
            ['Фантастика'],
            'witcher_ravens.jpeg',
            app
        )

        add_book(
            'Ведьмак: Последнее желание',
            'Описание будет добавлено позже.',
            1993,
            288,
            'SuperNowa',
            'Анджей Сапковский',
            ['Фантастика'],
            'witcher_lastwish.jpeg',
            app
        )

        add_book(
            'Ученик убийцы',
            'Описание будет добавлено позже.',
            1995,
            392,
            'Voyager',
            'Робин Хобб',
            ['Роман'],
            'assassin_apprentice.png',
            app
        )

        add_book(
            'Королевский убийца',
            'Описание будет добавлено позже.',
            1996,
            648,
            'Voyager',
            'Робин Хобб',
            ['Роман'],
            'royal_assassin.jpeg',
            app
        )

        print('База данных инициализирована.')


if __name__ == '__main__':
    main()
