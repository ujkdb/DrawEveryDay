import requests
from flask import Flask, render_template, redirect, request, abort
from flask_login import LoginManager, login_user, login_required, logout_user, current_user

from data import db_session

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
    return render_template("base.html")


@app.route('/login', methods=['GET'])
def login():
    return render_template('login_form.html')


@app.route('/post', methods=['GET'])
def post():
    response = requests.get("http://127.0.0.1:5000/login", params={'email': 'email', "password": "password"})
    json_response = response.json()
    repository = json_response["email"]
    print(repository)
    return render_template('base.html')


if __name__ == '__main__':
    main()
