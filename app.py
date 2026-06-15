"""
Entry point of the electronic library application.

This file sets up the Flask application, initialises the database and
login manager, defines helper decorators and implements all routes
required by the assignment.
"""

from __future__ import annotations

import os
import hashlib
from functools import wraps
from typing import Iterable

from flask import (
    Flask, render_template, redirect, url_for, flash,
    request, abort, send_from_directory
)
from flask_login import (
    LoginManager, login_user, logout_user, current_user,
    login_required
)
import markdown
import bleach

from config import Config
from models import db, Role, User, Genre, Book, Cover, BookGenre, Review, ReviewStatus


def create_app() -> Flask:
    """Factory function to create and configure the Flask application."""
    app = Flask(__name__)
    app.config.from_object(Config)

    # initialise database and login manager
    db.init_app(app)
    login_manager.init_app(app)

    # set login view for @login_required
    login_manager.login_view = 'login'
    # message shown when a non authenticated user tries to access a protected page
    login_manager.login_message = 'Для выполнения данного действия необходимо пройти процедуру аутентификации'
    login_manager.login_message_category = 'warning'

    # ensure covers directory exists
    covers_path = os.path.join(app.static_folder, 'covers')
    os.makedirs(covers_path, exist_ok=True)

    def create_tables() -> None:
        """Create database tables if they do not exist."""
        db.create_all()
        # insert initial roles and statuses if not present
        if not Role.query.first():
            roles = [
                Role(id=1, name='administrator', description='Superuser with full access to the system including creating and deleting books'),
                Role(id=2, name='moderator', description='Can edit books and moderate reviews'),
                Role(id=3, name='user', description='Can leave reviews')
            ]
            db.session.add_all(roles)
            db.session.commit()
        if not ReviewStatus.query.first():
            statuses = [
                ReviewStatus(id=1, name='pending'),
                ReviewStatus(id=2, name='approved'),
                ReviewStatus(id=3, name='rejected')
            ]
            db.session.add_all(statuses)
            db.session.commit()

    # allowed HTML tags for sanitising Markdown output
    ALLOWED_TAGS: list[str] = [
        'a', 'abbr', 'acronym', 'b', 'blockquote', 'code', 'em', 'i', 'li', 'ol',
        'strong', 'ul', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'p', 'pre'
    ]
    ALLOWED_ATTRIBUTES: dict[str, Iterable[str]] = {
        'a': ['href', 'title'],
        'abbr': ['title'],
        'acronym': ['title']
    }

    def render_markdown(text: str) -> str:
        """Converts Markdown to HTML and sanitises it."""
        html = markdown.markdown(text, extensions=['extra', 'codehilite'])
        clean = bleach.clean(html, tags=ALLOWED_TAGS, attributes=ALLOWED_ATTRIBUTES)
        return clean

    def role_required(*roles: str):
        """Decorator to restrict access to users with specified role names."""
        def decorator(fn):
            @wraps(fn)
            def wrapper(*args, **kwargs):
                if not current_user.is_authenticated:
                    return login_manager.unauthorized()
                if current_user.role.name not in roles:
                    # show message when user lacks necessary permissions
                    flash('У вас недостаточно прав для выполнения данного действия', 'warning')
                    return redirect(url_for('index'))
                return fn(*args, **kwargs)
            return wrapper
        return decorator

    @login_manager.user_loader
    def load_user(user_id: str) -> User | None:
        return User.query.get(int(user_id))

    @app.route('/')
    @app.route('/page/<int:page>')
    def index(page: int = 1):
        """Main page showing a paginated list of books."""
        books = Book.query.order_by(Book.year.desc()).paginate(page=page, per_page=app.config['POSTS_PER_PAGE'], error_out=False)
        return render_template('index.html', books=books)

    @app.route('/login', methods=['GET', 'POST'])
    def login():
        """Handles user login."""
        if current_user.is_authenticated:
            return redirect(url_for('index'))
        if request.method == 'POST':
            login_name = request.form.get('login')
            password = request.form.get('password')
            remember = request.form.get('remember') == 'on'
            user = User.query.filter_by(login=login_name).first()
            if user and user.check_password(password):
                login_user(user, remember=remember)
                next_page = request.args.get('next')
                return redirect(next_page or url_for('index'))
            flash('Невозможно аутентифицироваться с указанными логином и паролем', 'danger')
        return render_template('login.html')

    @app.route('/logout')
    @login_required
    def logout():
        """Logs out the current user."""
        logout_user()
        flash('Вы вышли из системы', 'info')
        return redirect(url_for('index'))

    @app.route('/book/add', methods=['GET', 'POST'])
    @login_required
    @role_required('administrator')
    def add_book():
        """Adds a new book to the system."""
        all_genres = Genre.query.order_by(Genre.name).all()
        if request.method == 'POST':
            # extract form values
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()
            year = request.form.get('year', type=int)
            pages = request.form.get('pages', type=int)
            publisher = request.form.get('publisher', '').strip()
            author = request.form.get('author', '').strip()
            genre_ids = request.form.getlist('genres')
            cover_file = request.files.get('cover')
            # basic validation
            if not title or not description or not year or not pages or not publisher or not author or not genre_ids or not cover_file:
                flash('Пожалуйста, заполните все обязательные поля.', 'danger')
            else:
                try:
                    # compute md5 of uploaded file
                    file_data = cover_file.read()
                    md5 = hashlib.md5(file_data).hexdigest()
                    # sanitise markdown text before storing
                    safe_description = bleach.clean(description)
                    # create book first because cover stores book_id
                    book = Book(title=title, description=safe_description, year=year, pages=pages,
                                publisher=publisher, author=author)
                    # assign genres
                    for gid in genre_ids:
                        genre = Genre.query.get(int(gid))
                        if genre:
                            book.genres_assoc.append(BookGenre(genre=genre))
                    db.session.add(book)
                    db.session.flush()
                    # check if the same image has already been uploaded
                    existing_cover = Cover.query.filter_by(md5_hash=md5).first()
                    cover = Cover(filename='', mime_type=cover_file.mimetype, md5_hash=md5, book_id=book.id)
                    db.session.add(cover)
                    db.session.flush()
                    if existing_cover:
                        # reuse already saved file name to avoid file duplication
                        cover.filename = existing_cover.filename
                        db.session.commit()
                    else:
                        # use cover id as a file name to avoid collisions
                        ext = os.path.splitext(cover_file.filename)[1]
                        cover.filename = f"{cover.id}{ext}"
                        db.session.commit()
                        # save cover file to disk after successful database save
                        save_path = os.path.join(app.static_folder, 'covers', cover.filename)
                        with open(save_path, 'wb') as f:
                            f.write(file_data)
                    flash('Книга успешно добавлена', 'success')
                    return redirect(url_for('view_book', book_id=book.id))
                except Exception:
                    db.session.rollback()
                    flash('При сохранении данных возникла ошибка. Проверьте корректность введённых данных.', 'danger')
        # selected genres list remains empty on initial load
        return render_template('book_form.html', book=None, all_genres=all_genres, selected_genres=[])

    @app.route('/book/<int:book_id>/edit', methods=['GET', 'POST'])
    @login_required
    @role_required('administrator', 'moderator')
    def edit_book(book_id: int):
        """Edits an existing book. Cover cannot be changed."""
        book = Book.query.get_or_404(book_id)
        all_genres = Genre.query.order_by(Genre.name).all()
        selected_genres = [assoc.genre_id for assoc in book.genres_assoc]
        if request.method == 'POST':
            title = request.form.get('title', '').strip()
            description = request.form.get('description', '').strip()
            year = request.form.get('year', type=int)
            pages = request.form.get('pages', type=int)
            publisher = request.form.get('publisher', '').strip()
            author = request.form.get('author', '').strip()
            genre_ids = request.form.getlist('genres')
            if not title or not description or not year or not pages or not publisher or not author or not genre_ids:
                flash('Пожалуйста, заполните все обязательные поля.', 'danger')
            else:
                try:
                    book.title = title
                    book.description = bleach.clean(description)
                    book.year = year
                    book.pages = pages
                    book.publisher = publisher
                    book.author = author
                    # update genres: remove old, add new
                    book.genres_assoc.clear()
                    for gid in genre_ids:
                        genre = Genre.query.get(int(gid))
                        if genre:
                            book.genres_assoc.append(BookGenre(genre=genre))
                    db.session.commit()
                    flash('Книга успешно обновлена', 'success')
                    return redirect(url_for('view_book', book_id=book.id))
                except Exception:
                    db.session.rollback()
                    flash('При сохранении данных возникла ошибка. Проверьте корректность введённых данных.', 'danger')
        return render_template('book_form.html', book=book, all_genres=all_genres, selected_genres=selected_genres)

    @app.route('/book/<int:book_id>/delete', methods=['POST'])
    @login_required
    @role_required('administrator')
    def delete_book(book_id: int):
        """Deletes a book and its related records."""
        book = Book.query.get_or_404(book_id)
        try:
            cover = book.cover
            filename = cover.filename if cover else None
            db.session.delete(book)
            db.session.commit()
            # remove the cover file only if no other cover record uses it
            if filename:
                same_file_count = Cover.query.filter_by(filename=filename).count()
                if same_file_count == 0:
                    file_path = os.path.join(app.static_folder, 'covers', filename)
                    try:
                        os.remove(file_path)
                    except FileNotFoundError:
                        pass
            flash('Книга успешно удалена', 'success')
        except Exception:
            db.session.rollback()
            flash('При удалении книги возникла ошибка', 'danger')
        return redirect(url_for('index'))

    @app.route('/book/<int:book_id>')
    def view_book(book_id: int):
        """Displays a single book and its approved reviews."""
        book = Book.query.get_or_404(book_id)
        # convert book description from markdown to HTML
        description_html = render_markdown(book.description)
        # user review if exists
        user_review = None
        user_review_html = None
        if current_user.is_authenticated:
            user_review = Review.query.filter_by(book_id=book.id, user_id=current_user.id).first()
            if user_review:
                user_review_html = render_markdown(user_review.text)
        # list of approved reviews from other users
        approved = ReviewStatus.query.filter_by(name='approved').first()
        review_tuples: list[tuple[Review, str]] = []
        if approved:
            reviews = Review.query.filter_by(book_id=book.id, status_id=approved.id).order_by(Review.created_at.desc()).all()
            for r in reviews:
                review_tuples.append((r, render_markdown(r.text)))
        return render_template('book_view.html', book=book, description_html=description_html,
                               user_review=user_review, user_review_html=user_review_html,
                               reviews=review_tuples)

    @app.route('/book/<int:book_id>/review', methods=['GET', 'POST'])
    @login_required
    def add_review(book_id: int):
        """Allows a user to add a review for a book."""
        book = Book.query.get_or_404(book_id)
        # user roles allowed to review
        if current_user.role.name not in ['user', 'moderator', 'administrator']:
            flash('У вас недостаточно прав для выполнения данного действия', 'warning')
            return redirect(url_for('view_book', book_id=book.id))
        existing_review = Review.query.filter_by(book_id=book.id, user_id=current_user.id).first()
        if existing_review:
            flash('Вы уже написали рецензию на эту книгу', 'warning')
            return redirect(url_for('view_book', book_id=book.id))
        if request.method == 'POST':
            rating = request.form.get('rating', type=int)
            text = request.form.get('text', '').strip()
            if rating is None or text == '':
                flash('Пожалуйста, укажите оценку и текст рецензии', 'danger')
            else:
                try:
                    status_pending = ReviewStatus.query.filter_by(name='pending').first()
                    safe_text = bleach.clean(text)
                    review = Review(book_id=book.id, user_id=current_user.id, rating=rating,
                                    text=safe_text, status=status_pending)
                    db.session.add(review)
                    db.session.commit()
                    flash('Ваша рецензия отправлена и ожидает модерации', 'success')
                    return redirect(url_for('view_book', book_id=book.id))
                except Exception:
                    db.session.rollback()
                    flash('При сохранении рецензии произошла ошибка', 'danger')
        return render_template('review_form.html', book=book)

    @app.route('/my-reviews')
    @login_required
    @role_required('user', 'moderator', 'administrator')
    def my_reviews():
        """Shows the list of reviews created by the current user."""
        reviews = Review.query.filter_by(user_id=current_user.id).order_by(Review.created_at.desc()).all()
        review_tuples: list[tuple[Review, str]] = []
        for r in reviews:
            review_tuples.append((r, render_markdown(r.text)))
        return render_template('my_reviews.html', reviews=review_tuples)

    @app.route('/moderation')
    @app.route('/moderation/page/<int:page>')
    @login_required
    @role_required('moderator', 'administrator')
    def moderate_reviews(page: int = 1):
        """Shows a list of pending reviews to be moderated."""
        pending = ReviewStatus.query.filter_by(name='pending').first()
        query = Review.query.filter_by(status_id=pending.id).order_by(Review.created_at.desc()) if pending else Review.query.filter(False)
        reviews = query.paginate(page=page, per_page=app.config['POSTS_PER_PAGE'], error_out=False)
        return render_template('moderation.html', reviews=reviews)

    @app.route('/moderation/<int:review_id>', methods=['GET', 'POST'])
    @login_required
    @role_required('moderator', 'administrator')
    def moderate_review(review_id: int):
        """Displays a single pending review and allows moderator to approve or reject it."""
        review = Review.query.get_or_404(review_id)
        if review.status.name != 'pending':
            flash('Эта рецензия уже была модератором рассмотрена', 'info')
            return redirect(url_for('moderate_reviews'))
        if request.method == 'POST':
            action = request.form.get('action')
            if action not in ['approve', 'reject']:
                abort(400)
            try:
                new_status = ReviewStatus.query.filter_by(name='approved' if action == 'approve' else 'rejected').first()
                review.status = new_status
                db.session.commit()
                flash('Статус рецензии обновлён', 'success')
            except Exception:
                db.session.rollback()
                flash('Ошибка при обновлении рецензии', 'danger')
            return redirect(url_for('moderate_reviews'))
        review_html = render_markdown(review.text)
        return render_template('review_moderate.html', review=review, review_html=review_html)

    # run database initialisation once when the application is created
    # call create_tables inside the app context so that tables and default data are set up
    with app.app_context():
        create_tables()
    return app


# instantiate login manager outside of factory so it can be referenced in decorators
login_manager = LoginManager()


if __name__ == '__main__':
    app = create_app()
    # Use PORT environment variable if set (e.g. to avoid conflicts on port 5000)
    import os
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, port=port)