import requests
from flask import Flask, render_template, redirect, request, abort
from flask_login import LoginManager, login_user, login_required, logout_user, current_user

from data import db_session
from forms.user import RegisterForm, LoginForm

from threading import Thread
import schedule
import time

app = Flask(__name__)
login_manager = LoginManager()
login_manager.init_app(app)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'


@login_manager.user_loader
def load_user(none):
    return 1


def main():
    db_session.global_init("draweveryday.db")
    app.run()


@app.route("/")
def index():
    return render_template("base.html", title='DrawEveryDay')


@app.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        """db_sess = db_session.create_session()
        user = db_sess.query(User).filter(User.email == form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user, remember=form.remember_me.data)"""
        return redirect("/")
        return render_template('login.html', message="Неправильный логин или пароль", form=form)
    return render_template('login_form.html', title='Авторизация', form=form)


@app.route('/register', methods=['GET', 'POST'])
def reqister():
    form = RegisterForm()
    if form.validate_on_submit():
        """if form.password.data != form.password_again.data:
            return render_template('register.html', title='Регистрация', form=form,
                                   message="Пароли не совпадают")
        db_sess = db_session.create_session()
        if db_sess.query(User).filter(User.email == form.email.data).first():
            return render_template('register.html', title='Регистрация', form=form,
                                   message="Такой пользователь уже есть")
        user = User(
            name=form.name.data,
            email=form.email.data,
            hashed_password=form.password.data
        )
        user.set_password(form.password.data)
        db_sess.add(user)
        db_sess.commit()"""
        return redirect('/')
    return render_template('register_form.html', title='Регистрация', form=form)


@app.route('/draw_task/<difficulty>')
def draw_task(difficulty):
    return render_template('draw_task.html', difficulty=difficulty,
                           image_cap='https://winx-fan.ru/800/600/https/pbs.twimg.com/media/EekZ0QAWAAEVCk4.jpg',
                           caption='зайчик',
                           fact='на самом деле, рыть норы — привычка кроликов. Зайцы же предпочитают обустраивать '
                                'свои гнёзда в неглубоких ямах.')


@app.route('/draw_task')
def draw_task_default():
    return draw_task('easy')


@app.route('/update_task/<difficulty>')
def update_task(difficulty):
    return redirect('/draw_task/' + difficulty)


def update_all_tasks():
    pass


def timing_update():
    schedule.every(1).days.do(update_all_tasks)
    while True:
        schedule.run_pending()
        time.sleep(3600)


if __name__ == '__main__':
    every_day_thread = Thread(target=timing_update, name='every_day')
    every_day_thread.start()

    main()

    every_day_thread.join()
