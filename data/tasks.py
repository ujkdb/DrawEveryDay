import sqlalchemy
from sqlalchemy import orm

from .db_session import SqlAlchemyBase


class Task(SqlAlchemyBase):
    __tablename__ = 'tasks'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.String, unique=True)
    difficulty = sqlalchemy.Column(sqlalchemy.Integer)
    description = sqlalchemy.Column(sqlalchemy.String)
    image = sqlalchemy.Column(sqlalchemy.String)

    pictures = orm.relation("Picture", back_populates='task')

    def __repr__(self):
        return f"<Task> {self.id} {self.name} {self.difficulty}"
