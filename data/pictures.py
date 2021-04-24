import sqlalchemy
from sqlalchemy import orm

from .db_session import SqlAlchemyBase


class Picture(SqlAlchemyBase):
    __tablename__ = 'pictures'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    name = sqlalchemy.Column(sqlalchemy.String)

    task_id = sqlalchemy.Column(sqlalchemy.Integer,
                                sqlalchemy.ForeignKey("tasks.id"))

    owner_id = sqlalchemy.Column(sqlalchemy.Integer,
                                 sqlalchemy.ForeignKey("users.id"))

    user = orm.relation('User')

    task = orm.relation('Task')

    def __repr__(self):
        return f'<Picture> {self.id} {self.name} {self.likes} {self.owner_id}'
