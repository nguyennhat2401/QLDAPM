import math

from flask import render_template, request, redirect, flash
from flask_login import login_user, logout_user, current_user

import dao
from __init__ import app, Login, db
from dao import load_course, count_course, UPLOAD_FOLDER
from decorators import annonymous_user
from models import Enrollment, Course, Lesson, UserRole


@Login.user_loader
def get_user(user_id):
    return dao.get_user_by_id(user_id)

@app.route("/")
def index():
    page = request.args.get('page', 1)
    course_id = request.args.get('course_id')
    kw = request.args.get('kw')
    course = load_course(coure_id=course_id, kw=kw, page=int(page))

    page_size = app.config["PAGE_SIZE"]
    total = count_course()

    return render_template('index.html',courses=course,pages=math.ceil(total/page_size))


@app.route("/profile")
def profile():
    user_courses = dao.get_courses_by_user_id(current_user.id)
    teaching_courses = []
    if current_user.role.name == "INSTRUCTOR":
        teaching_courses = Course.query.filter_by(instructor_id=current_user.id).all()

    return render_template("profile.html", user=current_user, user_courses=user_courses,teaching_courses=teaching_courses)

@app.route("/edit-profile", methods=["GET", "POST"])
def edit_profile():
    user = current_user
    if request.method == "POST":
        full_name = request.form.get("fullName")
        email = request.form.get("email")

        # Cập nhật thông tin
        user.fullName = full_name
        user.email = email

        db.session.commit()
        flash("Cập nhật thông tin thành công!", "success")
        return redirect("/profile")

    return render_template("edit_profile.html", user=user)



@app.route("/course/<int:course_id>")
@app.route("/course/<int:course_id>/lesson/<int:lesson_id>")
def course_detail(course_id, lesson_id=None):
    course = Course.query.get(course_id)
    if not course:
        return "Khóa học không tồn tại!", 404

    enrollment = Enrollment.query.filter_by(student_id=current_user.id, course_id=course_id).first()
    if not enrollment:
        return "Bạn chưa đăng ký khóa học này!", 403

    lessons = Lesson.query.filter_by(course_id=course_id).all()
    selected_lesson = Lesson.query.get(lesson_id) if lesson_id else None

    return render_template("course.html",
                           course=course,
                           lessons=lessons,
                           selected_lesson=selected_lesson,
                           enrollment=enrollment)


@app.route("/instructor/courses")
def instructor_courses():
    if current_user.role != UserRole.INSTRUCTOR:
        return "Bạn không có quyền truy cập!", 403

    courses = Course.query.filter_by(instructor_id=current_user.id).all()
    return render_template("instructor_course.html", courses=courses)


@app.route("/instructor/add-course", methods=["GET", "POST"])
def add_course():
    if current_user.role != UserRole.INSTRUCTOR:
        return "Bạn không có quyền truy cập!", 403

    if request.method == "POST":
        title = request.form.get("title")
        description = request.form.get("description")
        price = request.form.get("price", 0)

        lesson_titles = request.form.getlist("lesson_title")
        lesson_contents = request.form.getlist("lesson_content")

        if not lesson_titles or not any(title.strip() for title in lesson_titles):
            return "Bạn phải thêm ít nhất một bài học!", 400

        # Tạo khóa học
        course = Course(
            title=title,
            description=description,
            price=price,
            instructor_id=current_user.id
        )
        db.session.add(course)
        db.session.commit()

        # Thêm bài học cho khóa học
        for i in range(len(lesson_titles)):
            if lesson_titles[i].strip():
                lesson = Lesson(
                    title=lesson_titles[i],
                    content=lesson_contents[i],
                    course_id=course.id
                )
                db.session.add(lesson)

        db.session.commit()

        return redirect("/instructor/courses")

    return render_template("add_course.html")


@app.route("/instructor/delete-course/<int:course_id>", methods=["POST"])
def delete_course(course_id):
    if current_user.role != UserRole.INSTRUCTOR:
        return "Bạn không có quyền truy cập!", 403

    course = Course.query.get(course_id)
    if not course or course.instructor_id != current_user.id:
        return "Khóa học không tồn tại hoặc bạn không phải người tạo!", 404

    db.session.delete(course)  # Sẽ tự xóa lesson nhờ cascade
    db.session.commit()

    return redirect("/instructor/courses")

@app.route("/instructor/edit-course/<int:course_id>", methods=["GET", "POST"])
def edit_course(course_id):
    if current_user.role != UserRole.INSTRUCTOR:
        return "Bạn không có quyền truy cập!", 403

    course = Course.query.get(course_id)
    if not course or course.instructor_id != current_user.id:
        return "Khóa học không tồn tại hoặc bạn không phải người tạo!", 404

    if request.method == "POST":
        # Cập nhật thông tin khóa học
        course.title = request.form.get("title")
        course.description = request.form.get("description")
        course.price = request.form.get("price", 0)

        # Cập nhật bài học cũ
        lesson_ids = request.form.getlist("lesson_id")
        lesson_titles = request.form.getlist("lesson_title")
        lesson_contents = request.form.getlist("lesson_content")

        for i, lesson_id in enumerate(lesson_ids):
            lesson = Lesson.query.get(int(lesson_id))
            if lesson:
                lesson.title = lesson_titles[i]
                lesson.content = lesson_contents[i]

        # Thêm bài học mới
        new_titles = request.form.getlist("new_lesson_title")
        new_contents = request.form.getlist("new_lesson_content")

        for i in range(len(new_titles)):
            if new_titles[i].strip():
                new_lesson = Lesson(
                    title=new_titles[i],
                    content=new_contents[i],
                    course_id=course.id
                )
                db.session.add(new_lesson)

        db.session.commit()
        return redirect("/instructor/courses")

    lessons = Lesson.query.filter_by(course_id=course.id).all()
    return render_template("edit_course.html", course=course, lessons=lessons)


@app.route("/instructor/delete-lesson/<int:lesson_id>/<int:course_id>", methods=["POST"])
def delete_lesson(lesson_id, course_id):
    if current_user.role != UserRole.INSTRUCTOR:
        return "Bạn không có quyền truy cập!", 403

    lesson = Lesson.query.get(lesson_id)
    if not lesson:
        return "Bài học không tồn tại!", 404

    db.session.delete(lesson)
    db.session.commit()
    return redirect(f"/instructor/edit-course/{course_id}")


@app.route("/login", methods=['GET', 'POST'])
@annonymous_user
def login_process():
    err_msg = None
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        u = dao.auth_user(username=username, password=password)

        if u:
            if not u.is_approved:
                err_msg = "Tài khoản của bạn đang chờ duyệt. Vui lòng quay lại sau!"
            else:
                login_user(u)
                next_page = request.args.get('next')
                return redirect(next_page if next_page else '/')
        else:
            err_msg = "Sai tên đăng nhập hoặc mật khẩu!"

    return render_template('login.html', err_msg=err_msg)



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
        elif dao.get_user_by_email(email):  # thêm hàm get_user_by_email trong dao
            err_msg = "Email đã tồn tại!"
        elif dao.get_user_by_username(username):
            err_msg = "Tên đăng nhập đã tồn tại!"
        else:
            try:
                dao.add_user(username=username, password=password,
                             email=email, fullname=fullname, role=role,
                             evidence_file=evidence_file)
                return redirect('/login')
            except ValueError as e:
                err_msg = str(e)

    return render_template('register.html', err_msg=err_msg)

if __name__ == '__main__':
    app.run(debug=True)

