"""
This module defines database models for the electronic library.

The models are built using SQLAlchemy. Relationships are set up to
cascade deletions where appropriate. A few convenience methods (for example,
average_rating) are provided on the Book model to simplify
template logic. Passwords are stored hashed using Werkzeug helpers.
"""

from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash

# SQLAlchemy instance is created here and initialised in app.py
db = SQLAlchemy()


class Role(db.Model):
    """Represents a user role (administrator, moderator, user)."""
    __tablename__ = 'roles'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False, unique=True)
    description = db.Column(db.Text, nullable=False)
    users = db.relationship('User', backref='role', lazy=True)

    def __repr__(self):
        return f"<Role {self.name}>"


class User(db.Model):
    """Represents an application user."""
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    login = db.Column(db.String(64), nullable=False, unique=True)
    password_hash = db.Column(db.String(255), nullable=False)
    last_name = db.Column(db.String(64), nullable=False)
    first_name = db.Column(db.String(64), nullable=False)
    middle_name = db.Column(db.String(64))
    role_id = db.Column(db.Integer, db.ForeignKey('roles.id'), nullable=False)
    reviews = db.relationship('Review', backref='user', lazy=True)

    def set_password(self, password: str) -> None:
        """Hashes and stores the given password."""
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        """Checks a plain password against the stored hash."""
        return check_password_hash(self.password_hash, password)

    def full_name(self) -> str:
        """Returns the user's full name composed of last, first and middle names."""
        parts = [self.last_name, self.first_name]
        if self.middle_name:
            parts.append(self.middle_name)
        return ' '.join(parts)

    # Required by Flask-Login
    @property
    def is_authenticated(self) -> bool:
        return True

    @property
    def is_active(self) -> bool:
        return True

    @property
    def is_anonymous(self) -> bool:
        return False

    def get_id(self) -> str:
        return str(self.id)

    def __repr__(self):
        return f"<User {self.login}>"


class Genre(db.Model):
    """Represents a book genre."""
    __tablename__ = 'genres'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False, unique=True)
    books_assoc = db.relationship('BookGenre', back_populates='genre')

    def __repr__(self):
        return f"<Genre {self.name}>"


class BookGenre(db.Model):
    """Association table between books and genres."""
    __tablename__ = 'book_genres'
    book_id = db.Column(db.Integer, db.ForeignKey('books.id', ondelete='CASCADE'), primary_key=True)
    genre_id = db.Column(db.Integer, db.ForeignKey('genres.id', ondelete='CASCADE'), primary_key=True)
    book = db.relationship('Book', back_populates='genres_assoc')
    genre = db.relationship('Genre', back_populates='books_assoc')


class Cover(db.Model):
    """Represents the image associated with a book."""
    __tablename__ = 'covers'
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    mime_type = db.Column(db.String(64), nullable=False)
    md5_hash = db.Column(db.String(32), nullable=False)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id', ondelete='CASCADE'), nullable=False)

    def __repr__(self):
        return f"<Cover {self.filename}>"


class Book(db.Model):
    """Represents a book in the library."""
    __tablename__ = 'books'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    description = db.Column(db.Text, nullable=False)
    year = db.Column(db.Integer, nullable=False)
    publisher = db.Column(db.String(255), nullable=False)
    author = db.Column(db.String(255), nullable=False)
    pages = db.Column(db.Integer, nullable=False)
    cover = db.relationship('Cover', backref='book', cascade='all, delete-orphan', uselist=False)
    genres_assoc = db.relationship('BookGenre', back_populates='book', cascade='all, delete-orphan')
    reviews = db.relationship('Review', backref='book', cascade='all, delete-orphan')

    def average_rating(self) -> float | None:
        """Returns the average rating of approved reviews or None if no reviews."""
        ratings = [r.rating for r in self.reviews if r.status and r.status.name == 'approved']
        if not ratings:
            return None
        return sum(ratings) / len(ratings)

    def reviews_count(self) -> int:
        """Returns the number of approved reviews for the book."""
        return len([r for r in self.reviews if r.status and r.status.name == 'approved'])

    @property
    def genres_list(self) -> list[str]:
        """Returns a list of genre names for the book."""
        return [assoc.genre.name for assoc in self.genres_assoc]

    def __repr__(self):
        return f"<Book {self.title}>"


class ReviewStatus(db.Model):
    """Represents the status of a review (pending, approved, rejected)."""
    __tablename__ = 'review_statuses'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64), nullable=False, unique=True)
    reviews = db.relationship('Review', backref='status', lazy=True)

    def __repr__(self):
        return f"<ReviewStatus {self.name}>"


class Review(db.Model):
    """Represents a user review for a book."""
    __tablename__ = 'reviews'
    id = db.Column(db.Integer, primary_key=True)
    book_id = db.Column(db.Integer, db.ForeignKey('books.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    rating = db.Column(db.Integer, nullable=False)
    text = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, server_default=db.func.now())
    status_id = db.Column(db.Integer, db.ForeignKey('review_statuses.id'), nullable=False)

    def __repr__(self):
        return f"<Review {self.id} user={self.user_id} book={self.book_id} rating={self.rating}>"