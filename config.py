import os


class Config:
    """
    Basic configuration class.

    Attributes:
        SECRET_KEY (str): key used by Flask to sign session cookies
        SQLALCHEMY_DATABASE_URI (str): database connection string
        SQLALCHEMY_TRACK_MODIFICATIONS (bool): disables SQLAlchemy event system to save resources
        POSTS_PER_PAGE (int): number of items per page for pagination
    """

    # a strong secret key should be set in production
    SECRET_KEY = os.environ.get("SECRET_KEY", "this-should-be-changed")
    # use sqlite by default; can be replaced with mysql connection string
    BASEDIR = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{os.path.join(BASEDIR, 'app.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    # number of books or reviews per page
    POSTS_PER_PAGE = 10