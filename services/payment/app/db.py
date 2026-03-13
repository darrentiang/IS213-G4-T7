# creates the database object shared across files
# prevent circular import

from flask_sqlalchemy import SQLAlchemy  # imports the database toolkit
db = SQLAlchemy()                        # creates one database "manager" object

