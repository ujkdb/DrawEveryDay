import sys
import random
import os
import requests
from flask import Flask, render_template, redirect, request, abort
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.utils import secure_filename

from data import db_session
from data.pictures import Picture
from forms.user import RegisterForm, LoginForm
from data.users import User
from data.tasks import Task
from forms.picture import UploadForm

from threading import Thread
import schedule
import time

app = Flask(__name__)
login_manager = LoginManager()
login_manager.init_app(app)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'


@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.query(User).get(user_id)


def get_file_extension(filename: str):
    filename = filename[::-1]
    filename = filename[:filename.find('.')]
    return '.' + filename[::-1]


def main():
    db_session.global_init("db/draweveryday.db")
    app.run()


@app.route("/")
def index():
    os.chdir(os.path.dirname(sys.argv[0]) + '/static/users_pictures')
    return render_template('gallery.html', files=os.listdir())


@app.route('/discover_image/<picture_name>')
def discover_image(picture_name):
    db_sess = db_session.create_session()
    picture = db_sess.query(Picture).filter(Picture.name == picture_name).first()
    user = db_sess.query(User).filter(User.id == picture.owner_id).first()
    task = db_sess.query(Task).filter(Task.id == picture.task_id).first()

    return render_template('discover_image.html', username=user.name, task=task.name.capitalize(),
                           picture_name=picture_name, task_difficulty=task.difficulty, user_id=user.id)


@app.route('/user/<int:user_id>')
def show_user(user_id):
    db_sess = db_session.create_session()
    user = db_sess.query(User).filter(User.id == user_id).first()
    images = map(lambda x: x.name, db_sess.query(Picture).filter(Picture.owner_id == user_id).all())

    os.chdir(os.path.dirname(sys.argv[0]) + '/static/users_pictures')
    files = list(filter(lambda x: x in images, os.listdir()))

    your_account = current_user.is_authenticated and current_user.id == user_id

    return render_template('show_user.html', username=user.name, files=files,
                           your_account=your_account, pic=user.get_rank_picture())


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.email == form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)
            return redirect("/")
        return render_template('login_form.html', message="Неправильный логин или пароль", form=form)
    return render_template('login_form.html', title='Авторизация', form=form)


@app.route('/register', methods=['GET', 'POST'])
def reqister():
    form = RegisterForm()
    if form.validate_on_submit():
        if form.password.data != form.password_again.data:
            return render_template('register_form.html', title='Регистрация', form=form,
                                   message="Пароли не совпадают")
        db_sess = db_session.create_session()
        if db_sess.query(User).filter(User.email == form.email.data).first():
            return render_template('register_form.html', title='Регистрация', form=form,
                                   message="Такой пользователь уже есть")
        user = User(
            name=form.name.data,
            email=form.email.data,
            hashed_password=form.password.data,
            current_task=add_random_task().id
        )
        user.set_password(form.password.data)
        db_sess.add(user)
        db_sess.commit()
        return redirect('/')
    return render_template('register_form.html', title='Регистрация', form=form)


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect("/")


def add_random_task(difficulty=0):
    db_sess = db_session.create_session()
    tasks = db_sess.query(Task).filter(Task.difficulty == difficulty).all()
    task = random.choice(tasks)
    return task


@app.route('/draw_task/', methods=['GET', 'POST'])
def draw_task():
    if not current_user.is_authenticated:
        return redirect('/login')
    form = UploadForm()
    task = db_session.create_session().query(Task).filter(Task.id == current_user.current_task).first()
    difficulty = ('easy', 'medium', 'hard')[task.difficulty]
    if form.validate_on_submit():
        f = form.picture.data
        filename = f.filename
        if not (filename.endswith(".jpg") or filename.endswith(".jpeg") or filename.endswith(".png")):
            return render_template('draw_task.html', form=form, difficulty=difficulty,
                                   image_cap=task.image,
                                   caption=task.name,
                                   fact=task.description,
                                   error_message="Неверный формат")
        db_sess = db_session.create_session()
        if db_sess.query(Picture).filter(
                Picture.task_id == task.id).filter(Picture.owner_id == current_user.id).first():
            return render_template('draw_task.html', form=form, difficulty=difficulty,
                                   image_cap=task.image,
                                   caption=task.name,
                                   fact=task.description,
                                   error_message="Вы уже отправляли это задание")
        picture = Picture(
            name=filename,
            owner_id=current_user.id,
            task_id=task.id
        )
        db_sess.add(picture)
        db_sess.commit()

        picture.name = str(picture.id) + get_file_extension(picture.name)

        score = current_user.score.split(';')
        score[task.difficulty] = str(int(score[task.difficulty]) + 1)
        current_user.score = ';'.join(score)
        current_user.check_rank()

        db_sess.merge(current_user)
        db_sess.merge(picture)
        db_sess.commit()

        f.save(os.path.join(
            'static/users_pictures/', picture.name
        ))

        return render_template('draw_task.html', form=form, difficulty=difficulty,
                               image_cap=task.image,
                               caption=task.name,
                               fact=task.description,
                               done_message="Рисунок отправлен!")
    return render_template('draw_task.html', form=form, difficulty=difficulty,
                           image_cap=task.image,
                           caption=task.name,
                           fact=task.description)


@app.route('/draw_task/<int:task>/')
def show_task(task):
    if not (current_user.is_authenticated and current_user.name == 'admin'):
        return 'You can\'t access to this page'

    task = db_session.create_session().query(Task).filter(Task.id == task).first()
    difficulty = ('easy', 'medium', 'hard')[task.difficulty]
    return render_template('draw_task.html', difficulty=difficulty,
                           image_cap=task.image,
                           caption=task.name,
                           fact=task.description)


@app.route('/update_task/<difficulty>')
def update_task(difficulty):
    if not current_user.is_authenticated:
        return redirect('/login')

    task = add_random_task({'easy': 0, 'medium': 1, 'hard': 2}[difficulty])
    current_user.current_task = task.id
    db_sess = db_session.create_session()
    db_sess.merge(current_user)
    db_sess.commit()
    return redirect('/draw_task')


@app.route('/update_all_task')
def update_all_tasks():
    if not (current_user.is_authenticated and current_user.name == 'admin'):
        return 'You can\'t access to this page'

    db_sess = db_session.create_session()
    for user in db_sess.query(User).all():
        task = db_sess.query(Task).filter(Task.id == user.current_task).first()
        user.current_task = add_random_task(task.difficulty).id
        db_sess.merge(user)
    db_sess.commit()
    return redirect('/draw_task')


def timing_update():
    schedule.every(1).days.do(update_all_tasks)
    while True:
        schedule.run_pending()
        time.sleep(3600)


@app.route('/user_data')
def user_data():
    if current_user.is_authenticated:
        return current_user.name
    return 'anonymous'


@app.route('/check_random')
def check_random():
    if not (current_user.is_authenticated and current_user.name == 'admin'):
        return 'You can\'t access to this page'

    easy = [add_random_task(0) for _ in range(100)]
    medium = [add_random_task(1) for _ in range(100)]
    hard = [add_random_task(2) for _ in range(100)]

    return str(easy) + '<br>' + str(medium) + '<br>' + str(hard)


@app.route('/close_server')
def stop_server():
    if not (current_user.is_authenticated and current_user.name == 'admin'):
        return 'You can\'t access to this page'

    sys.exit()


@app.route('/authors_information')
def authors_information():
    return render_template('author_information.html')


@app.route('/license_information')
def license_information():
    return render_template('license_information.html')


@app.route('/statistics')
def stats():
    if not current_user.is_authenticated:
        return redirect('/login')

    score_num = current_user.get_score_num()

    easy, medium, hard = map(int, current_user.score.split(';'))
    total = easy + medium + hard

    prefers = current_user.prefer_difficulty()
    len_prefers = sum(map(lambda x: 1 if prefers[x] else 0, prefers.keys()))
    if len_prefers == 3:
        prefers = 'У вас не наблюдается приверженности какой-то конкретной ' \
                  'сложности. \nВаш баланс вызывает зависть даже у Таноса.'
    elif len_prefers == 2:
        if prefers['easy'] and prefers['medium']:
            prefers = 'У вас наблюдается склонность к лёгкой и средней сложности. \n' \
                      'Следующим этапом, должно быть, будет сложная?'
        elif prefers['easy'] and prefers['hard']:
            prefers = 'У вас наблюдается склонность к лёгкой и сложной сложности. \n' \
                      'Вы — человек контрастов.'
        else:
            prefers = 'У вас наблюдается склонность к средней и сложной сложности. \n' \
                      'Очевидно, что вы профессионал, но не стоит ' \
                      'пренебрегать лёгкой сложностью — она тоже может Вас удивить.'
    else:
        prefers = {'easy': 'Вы склонны к выбору лёгкой сложности. Это прекрасно, Вам ещё есть куда расти!',
                   'medium': 'Вы склонны к выбору средней сложности. \nНадеемся, '
                             'Вы продолжите поднимать планку и ставить вызовы своему мастерству.',
                   'hard': 'Вы склонны к выбору сложной сложности. \nНет сомнений, Вы — мастер. '
                           'Благо, у вас ещё есть шанс поставить себе вызов, попробовав уровни пониже.'
                   }[next(filter(lambda x: prefers[x], prefers.keys()))]

    return render_template('statistics.html', score_num=score_num,
                           procents=score_num * 10 // current_user.rank,
                           easy=easy * 100 // total, medium=medium * 100 // total,
                           hard=hard * 100 // total, prefers=prefers, post_scriptum=prefers)


if __name__ == '__main__':
    every_day_thread = Thread(target=timing_update, name='every_day')
    every_day_thread.start()

    main()

    every_day_thread.join()
