import sqlalchemy
from flask_login import UserMixin
from sqlalchemy import orm
from werkzeug.security import generate_password_hash, check_password_hash

from .db_session import SqlAlchemyBase


class User(SqlAlchemyBase, UserMixin):
    __tablename__ = 'users'

    id = sqlalchemy.Column(sqlalchemy.Integer, primary_key=True, autoincrement=True)
    email = sqlalchemy.Column(sqlalchemy.String, unique=True)
    hashed_password = sqlalchemy.Column(sqlalchemy.String)
    name = sqlalchemy.Column(sqlalchemy.String, unique=True)
    current_task = sqlalchemy.Column(sqlalchemy.Integer)
    rank = sqlalchemy.Column(sqlalchemy.Integer, default=1)
    score = sqlalchemy.Column(sqlalchemy.String, default='0;0;0')

    # pictures = orm.relation("Picture", back_populates='user')

    def __repr__(self):
        return f'<User> {self.id} {self.name} {self.email}'

    def set_password(self, password):
        self.hashed_password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.hashed_password, password)

    def convert_to_points(self, difficulty, count):
        count = int(count)
        if difficulty == 0:
            return count
        elif difficulty == 1:
            return int(count * 1.5)
        else:
            return count * 2

    def get_score_num(self):
        return sum(map(lambda x: self.convert_to_points(*x),
                       enumerate(self.score.split(';'))))

    def check_rank(self):
        if self.rank * 10 <= self.get_score_num():
            self.rank += 1

    def prefer_difficulty(self):
        result = {'easy': False, 'medium': False, 'hard': False}

        easy, medium, hard = map(int, self.score.split(';'))
        max_score = max((easy, medium, hard))
        for key in result.keys():
            if locals()[key] == max_score:
                result[key] = True
        return result

    def get_rank_picture(self):
        return ('', 'person', 'artist', 'knight', 'wizard', 'king')[self.rank]
