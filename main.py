# импорт библиотек
from waitress import serve
import sys
import random
import os
from threading import Thread
import schedule
import time
from flask import Flask, render_template, redirect
from flask_login import LoginManager, login_user, login_required, logout_user, current_user

# импорт файлов и классов
from data import db_session
from data.pictures import Picture
from data.users import User
from data.tasks import Task
from forms.user import RegisterForm, LoginForm
from forms.picture import UploadForm

# создание приложения
app = Flask(__name__)
login_manager = LoginManager()
login_manager.init_app(app)
app.config['SECRET_KEY'] = 'yandexlyceum_secret_key'


# загрузка текущего пользователя сайта
@login_manager.user_loader
def load_user(user_id):
    db_sess = db_session.create_session()
    return db_sess.query(User).get(user_id)


# получить расширение по имени файла
def get_file_extension(filename: str):
    filename = filename[::-1]
    filename = filename[:filename.find('.')]
    return '.' + filename[::-1]


"""Галерея изображений"""


# страница галереи
@app.route("/")
def index():
    # возвращаем шаблон с рисунками
    return render_template('gallery.html', files=os.listdir())


# просмотр отдельного изображения
@app.route('/discover_image/<picture_name>')
def discover_image(picture_name):
    # создаем сессию с базой данных
    db_sess = db_session.create_session()
    # получаем название рисунка
    picture = db_sess.query(Picture).filter(Picture.name == picture_name).filter(Picture.deleted == 0).first()

    if not picture:  # если изображения не существует
        return redirect('/')

    your_image = current_user.is_authenticated and current_user.id == picture.owner_id

    # получаем id автора
    user = db_sess.query(User).filter(User.id == picture.owner_id).first()
    # получаем id задания
    task = db_sess.query(Task).filter(Task.id == picture.task_id).first()
    # возвращаем шаблон с изображением, именем автора, заданием, именем рисунка, сложностью задания и id пользователя
    return render_template('discover_image.html', username=user.name, task=task.name.capitalize(),
                           picture_name=picture_name, task_difficulty=task.difficulty, user_id=user.id,
                           your_image=your_image, picture_id=picture.id)


"""Авторизация, регистрация и выход из учетной записи"""


# Авторизация
@app.route('/login', methods=['GET', 'POST'])
def login():
    # создаем экземпляр класса формы
    form = LoginForm()
    # если форма заполнена
    if form.validate_on_submit():
        # создаем сессию с базой данных
        db_sess = db_session.create_session()
        # находим пользователя по email
        user = db_sess.query(User).filter(User.email == form.email.data).first()
        # сверяем введеный логин и пароль с данными из базы данных
        if user and user.check_password(form.password.data):
            # если все хорошо, запоминаем текущего пеользователя с помощью login_user
            login_user(user, remember=form.remember_me.data)
            # и перенаправляем на галерею
            return redirect("/")
        # если пользователь ввёл неправильный логин или пароль, возвращаем шаблон и сообщаем ему об этом
        return render_template('login_form.html', message="Неправильный логин или пароль", form=form)
    # возвращаем шаблон с заголовком и формой, если пользователь её не заполнил
    return render_template('login_form.html', form=form)


# Выход из учетной записи
@app.route('/logout')
@login_required
def logout():
    # выходим из учетной записи
    logout_user()
    # и перенаправляем на галерею
    return redirect("/")


# Регистрация
@app.route('/register', methods=['GET', 'POST'])
def reqister():
    # создаем экземпляр класса формы
    form = RegisterForm()
    # если форма заполнена
    if form.validate_on_submit():
        # сверяем пароли
        if form.password.data != form.password_again.data:
            # если пользователь ввёл несовпадающие пароли, возвращаем шаблон и сообщаем ему об этом
            return render_template('register_form.html', form=form,
                                   message="Пароли не совпадают")
        # создаем сессию с базой данных
        db_sess = db_session.create_session()
        # проверяем, есть ли уже в базе данных пользователь с введенной почтой
        if db_sess.query(User).filter(User.email == form.email.data).first():
            # если да, возвращаем шаблон и сообщаем ему об этом
            return render_template('register_form.html', form=form,
                                   message="Такой пользователь уже есть")
        # создаем новую запись
        user = User(
            name=form.name.data,
            email=form.email.data,
            hashed_password=form.password.data,
            current_task=add_random_task().id
        )
        # создаем хэш-пароль
        user.set_password(form.password.data)
        # добавляем запись и сохраняем
        db_sess.add(user)
        db_sess.commit()
        # перенаправляем на галерею
        return redirect('/')
    # возвращаем шаблон с заголовком и формой, если пользователь её не заполнил
    return render_template('register_form.html', form=form)


"""Профиль пользователя"""


@app.route('/user/<int:user_id>')
def show_user(user_id):
    # создаем сессию с базой данных
    db_sess = db_session.create_session()
    # находим пользователя
    user = db_sess.query(User).filter(User.id == user_id).first()
    # находим его рисунки в базе данных
    images = map(lambda x: x.name, db_sess.query(Picture).filter(Picture.owner_id == user_id).all())

    # находим файлы рисунков
    os.chdir(os.path.dirname(sys.argv[0]) + '/static/users_pictures')
    files = list(filter(lambda x: x in images, os.listdir()))

    # узнаем свой это или чужой аккаунт
    your_account = current_user.is_authenticated and current_user.id == user_id

    # возвращаем шаблон с изображением, именем пользователя, рисунками и информацией, свой ли это аккаунт
    return render_template('show_user.html', username=user.name, files=files, pic=user.get_rank_picture(),
                           your_account=your_account)


"""Загрузка и удаление рисунков по заданиям"""


@app.route('/draw_task/', methods=['GET', 'POST'])
def draw_task():
    # зарегистрирован ли пользователь
    if not current_user.is_authenticated:
        return redirect('/login')
    # создаем экземпляр класса формы
    form = UploadForm()
    # узнаем текущее задание для пользователя
    task = db_session.create_session().query(Task).filter(Task.id == current_user.current_task).first()
    # сложность задания
    difficulty = ('easy', 'medium', 'hard')[task.difficulty]
    # если форма заполнена
    if form.validate_on_submit():
        # получаем рисунок
        f = form.picture.data
        # получаем его имя
        filename = f.filename
        # проверяем формат файла
        if not (filename.endswith(".jpg") or filename.endswith(".jpeg") or filename.endswith(".png")):
            # если пользователь отправил файл с неправильным форматом, возвращаем шаблон и сообщаем ему об этом
            return render_template('draw_task.html', form=form, difficulty=difficulty,
                                   image_cap=task.image,
                                   caption=task.name,
                                   fact=task.description,
                                   error_message="Неверный формат")
        # создаем сессию с базой данных
        db_sess = db_session.create_session()
        # проверяем, отправлял ли пользователь это задание в прошлом
        if db_sess.query(Picture).filter(Picture.task_id == task.id).\
                filter(Picture.owner_id == current_user.id).\
                filter(Picture.deleted == 0).first():
            # если да, возвращаем шаблон и сообщаем ему об этом
            return render_template('draw_task.html', form=form, difficulty=difficulty,
                                   image_cap=task.image,
                                   caption=task.name,
                                   fact=task.description,
                                   error_message="Вы уже отправляли это задание")

        picture = db_sess.query(Picture).filter(  # если запись об изображении есть в удалённом виде
            Picture.task_id == task.id).filter(Picture.owner_id == current_user.id).first()

        if picture:
            picture.name = filename
            picture.deleted = False
        else:
            # создаем новую запись
            picture = Picture(
                name=filename,
                owner_id=current_user.id,
                task_id=task.id
            )
            # добавляем ее и сохраняем
            db_sess.add(picture)

            current_user.add_picture_points(task.difficulty)
            db_sess.merge(current_user)

            db_sess.commit()

        # делим файл на название и формат
        split_filename = os.path.splitext(picture.name)
        # переименовываем рисунок по его id
        picture.name = str(picture.id) + split_filename[-1]
        # добавляем и сохраняем изменения
        db_sess.merge(picture)
        db_sess.commit()

        # сохраняем файл
        f.save(os.path.join(
            os.getcwd(), picture.name
        ))
        # и пишем пользовалелю об успешной отправке рисунка
        return render_template('draw_task.html', form=form, difficulty=difficulty,
                               image_cap=task.image,
                               caption=task.name,
                               fact=task.description,
                               done_message="Рисунок отправлен!")
    # возвращаем шаблон с формой; сложностью, изображением, названием и описанием задания,
    # если пользователь не загрузил рисунок
    return render_template('draw_task.html', form=form, difficulty=difficulty,
                           image_cap=task.image,
                           caption=task.name,
                           fact=task.description)


@app.route('/delete_image/<int:image_id>')
def delete_image(image_id):
    if not current_user.is_authenticated:
        return redirect('/login')

    db_sess = db_session.create_session()
    picture = db_sess.query(Picture).filter(Picture.id == image_id).first()

    if current_user.id == picture.owner_id:
        os.remove(os.path.join(os.getcwd(), picture.name))  # удаляем изображение
        picture.deleted = True  # определяем изображение, как удалённое

        db_sess.merge(picture)
        db_sess.commit()

    return redirect('/')


"""Получение отдельного задания (для разработчиков)"""


@app.route('/draw_task/<int:task>/')
def show_task(task):
    # воспрещаем доступ если пользователь не является админом
    if not (current_user.is_authenticated and current_user.name == 'admin'):
        return 'You can\'t access to this page'

    # создаем экземпляр класса формы
    form = UploadForm()
    # находим нужное нам задание
    task = db_session.create_session().query(Task).filter(Task.id == task).first()
    difficulty = ('easy', 'medium', 'hard')[task.difficulty]
    # выводим шаблон
    return render_template('draw_task.html', form=form, difficulty=difficulty,
                           image_cap=task.image,
                           caption=task.name,
                           fact=task.description)


"""Добавление случайного и обновление задания и проверка рандома"""


# обновление задания для пользователя
@app.route('/update_task/<difficulty>')
def update_task(difficulty):
    # если не зарегестрирован перенаправляем на авторизацию
    if not current_user.is_authenticated:
        return redirect('/login')
    # случайно выбираем задание
    task = add_random_task({'easy': 0, 'medium': 1, 'hard': 2}[difficulty])
    # и сохраняем его в базе данных для текущего пользователя
    current_user.current_task = task.id
    db_sess = db_session.create_session()
    db_sess.merge(current_user)
    db_sess.commit()
    # перенаправляем на загрузку рисунков
    return redirect('/draw_task')


# добавление случайного задания
def add_random_task(difficulty=0):
    # подключаемся к бд
    db_sess = db_session.create_session()
    # получаем список всех заданий
    tasks = db_sess.query(Task).filter(Task.difficulty == difficulty).all()
    # выбираем случайное и возвращаем его
    task = random.choice(tasks)
    return task


# проверка рандома (для разработчиков)
@app.route('/check_random')
def check_random():
    if not (current_user.is_authenticated and current_user.name == 'admin'):
        return 'You can\'t access to this page'

    easy = [add_random_task(0) for _ in range(100)]
    medium = [add_random_task(1) for _ in range(100)]
    hard = [add_random_task(2) for _ in range(100)]

    return str(easy) + '<br>' + str(medium) + '<br>' + str(hard)


"""Статистика"""


@app.route('/statistics')
def stats():
    if not current_user.is_authenticated:
        return redirect('/login')

    score_num = current_user.get_score_num()  # счёт для шкалы уровня

    # значения для шкалы предпочтения сложности
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
    if total != 0:
        return render_template('statistics.html', score_num=score_num,
                               procents=score_num * 10 // current_user.rank,
                               easy=easy * 100 // total, medium=medium * 100 // total,
                               hard=hard * 100 // total, prefers=prefers, post_scriptum=prefers)
    return render_template('statistics.html', score_num=score_num,
                           procents=score_num * 10 // current_user.rank,
                           easy=0, medium=0,
                           hard=0, prefers=prefers, post_scriptum=prefers)


"""Ассинхронное обновление заданий"""


# обновление всех заданий для всех пользоватей
@app.route('/update_all_task')
def update_all_tasks():
    # воспрещаем доступ если пользователь не является админом
    if not (current_user.is_authenticated and current_user.name == 'admin'):
        return 'You can not access to this page'
    # подключаемся к бд
    db_sess = db_session.create_session()
    # перебираем всех пользователей и обновляем у каждого задание
    for user in db_sess.query(User).all():
        task = db_sess.query(Task).filter(Task.id == user.current_task).first()
        user.current_task = add_random_task(task.difficulty).id
        db_sess.merge(user)
        # сохраняем изменения
    db_sess.commit()
    # перенаправляем на загрузку рисунков
    return redirect('/draw_task')


def timing_update():
    # через каждый день запускаем функцию update_all_tasks
    schedule.every(1).days.do(update_all_tasks)
    # запускаем бесконечный цикл в котором каждый час проверяем есть ли задание (так ведь??????????????????)
    while True:
        schedule.run_pending()
        time.sleep(3600)


"""Информация об авторах и лицензии"""


# Информация об авторах
@app.route('/authors_information')
def authors_information():
    return render_template('author_information.html')


# Информация о лицензии
@app.route('/license_information')
def license_information():
    return render_template('license_information.html')


"""Запускающая приложение функция"""


def main():
    # подключаем базу данных для создания сессий с ней
    db_session.global_init("db/draweveryday.db")

    os.chdir(os.getcwd() + '/static/users_pictures')  # смена директории для галереи

    # запускаем приложение
    serve(app, host="0.0.0.0", port=5000)


if __name__ == '__main__':
    # создаем поток
    every_day_thread = Thread(target=timing_update, name='every_day')
    # запускаем
    every_day_thread.start()

    # вызываем main
    main()

    every_day_thread.join()  # обрубаем концы потока
