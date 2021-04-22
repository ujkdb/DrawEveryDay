import sqlalchemy
from flask_login import UserMixin

from .db_session import SqlAlchemyBase


class Task(SqlAlchemyBase, UserMixin):
    __tablename__ = 'tasks'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.String, unique=True)
    difficulty = sqlalchemy.Column(sqlalchemy.Integer)
    description = sqlalchemy.Column(sqlalchemy.String)
    image = sqlalchemy.Column(sqlalchemy.String)

    def __repr__(self):
        return self.name
