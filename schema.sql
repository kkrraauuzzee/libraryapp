-- Database schema for the electronic library application
-- Tables are named in English and include primary keys, foreign keys
-- with ON DELETE CASCADE where appropriate to automatically
-- delete dependent records.

-- Roles table: defines the three roles used by the application
CREATE TABLE roles (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(64) NOT NULL UNIQUE,
    description TEXT NOT NULL
);

-- Users table: stores account information
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    login VARCHAR(64) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    last_name VARCHAR(64) NOT NULL,
    first_name VARCHAR(64) NOT NULL,
    middle_name VARCHAR(64) DEFAULT NULL,
    role_id INT NOT NULL,
    FOREIGN KEY (role_id) REFERENCES roles(id)
);

-- Review statuses table: defines possible review states
CREATE TABLE review_statuses (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(64) NOT NULL UNIQUE
);

-- Genres table: stores book genres
CREATE TABLE genres (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(64) NOT NULL UNIQUE
);

-- Books table: stores books
CREATE TABLE books (
    id INT AUTO_INCREMENT PRIMARY KEY,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    year INT NOT NULL,
    publisher VARCHAR(255) NOT NULL,
    author VARCHAR(255) NOT NULL,
    pages INT NOT NULL
);

-- Covers table: stores book cover metadata
CREATE TABLE covers (
    id INT AUTO_INCREMENT PRIMARY KEY,
    filename VARCHAR(255) NOT NULL,
    mime_type VARCHAR(64) NOT NULL,
    md5_hash VARCHAR(32) NOT NULL,
    book_id INT NOT NULL,
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE
);

-- Association table between books and genres
CREATE TABLE book_genres (
    book_id INT NOT NULL,
    genre_id INT NOT NULL,
    PRIMARY KEY (book_id, genre_id),
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
    FOREIGN KEY (genre_id) REFERENCES genres(id) ON DELETE CASCADE
);

-- Reviews table: stores user reviews on books
CREATE TABLE reviews (
    id INT AUTO_INCREMENT PRIMARY KEY,
    book_id INT NOT NULL,
    user_id INT NOT NULL,
    rating INT NOT NULL,
    text TEXT NOT NULL,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
    status_id INT NOT NULL,
    FOREIGN KEY (book_id) REFERENCES books(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (status_id) REFERENCES review_statuses(id)
);

-- Insert initial role values
INSERT INTO roles (id, name, description) VALUES
    (1, 'administrator', 'Superuser with full access to the system including creating and deleting books'),
    (2, 'moderator', 'Can edit books and moderate reviews'),
    (3, 'user', 'Can leave reviews');

-- Insert initial review statuses
INSERT INTO review_statuses (id, name) VALUES
    (1, 'pending'),
    (2, 'approved'),
    (3, 'rejected');