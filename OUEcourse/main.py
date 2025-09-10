import math

from flask import render_template, request, redirect
from flask_login import login_user, logout_user

import dao
from __init__ import app, Login
from dao import load_course, count_course
from decorators import annonymous_user

@Login.user_loader
def get_user(user_id):
    return dao.get_user_by_ID(user_id)

@app.route("/")
def index():
    page = request.args.get('page', 1)
    course_id = request.args.get('course_id')
    kw = request.args.get('kw')
    course = load_course(coure_id=course_id, kw=kw, page=int(page))

    page_size = app.config["PAGE_SIZE"]
    total = count_course()

    return render_template('index.html',courses=course,pages=math.ceil(total/page_size))


@app.route("/login", methods=['get','post'])
@annonymous_user

def login_process():
    if request.method.__eq__('POST'):
        username=request.form.get('username')
        password=request.form.get('password')
        u=dao.auth_user(username=username, password=password)
        if u:
            login_user(u)
            next = request.args.get('next')
            return redirect(next if next else '/')
    return render_template('login.html')

@app.route("/logout")
def logout_process():
    logout_user()
    return redirect('/login')

@app.route("/register", methods=['GET', 'POST'])
@annonymous_user
def register_process():
    err_msg = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm = request.form.get('confirm')
        email = request.form.get('email')
        fullname = request.form.get('fullname')
        role = request.form.get('role')
        evidence_file = request.files.get('evidence')

        if password != confirm:
            err_msg = "Mật khẩu không khớp!"
        else:
            dao.add_user(username=username, password=password,
                         email=email, fullname=fullname, role=role,
                         evidence_file=evidence_file)
            return redirect('/login')

    return render_template('register.html', err_msg=err_msg)

if __name__ == '__main__':
    app.run(debug=True)

