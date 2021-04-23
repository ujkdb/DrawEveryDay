import random
import os
import requests
from flask import Flask, render_template, redirect, request, abort
from flask_login import LoginManager, login_user, login_required, logout_user, current_user
from werkzeug.utils import secure_filename

from data import db_session
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


def main():
    db_session.global_init("db/draweveryday.db")
    app.run()


@app.route("/")
def index():
    return render_template('gallery.html', files=['../static/img/draw_icon.png'] * 9)


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
        filename = secure_filename(f.filename)
        f.save(os.path.join(
            'users_pictures', filename
        ))
        return redirect('/')
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


if __name__ == '__main__':
    every_day_thread = Thread(target=timing_update, name='every_day')
    every_day_thread.start()

    main()

    every_day_thread.join()
