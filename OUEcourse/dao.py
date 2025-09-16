import hashlib
import os

from flask_login import current_user
from werkzeug.utils import secure_filename

from models import User, Lesson, Course, Enrollment
from __init__ import app,db


def auth_user(username,password,role=None):
    password=str(hashlib.md5(password.encode('utf-8')).hexdigest())
    return User.query.filter(User.username.__eq__(username),User.password.__eq__(password)).first()

UPLOAD_FOLDER = "static/evidence"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def add_user(username, password, email, fullname, role, evidence_file=None):

    password = hashlib.md5(password.encode('utf-8')).hexdigest()
    is_approved = True
    evidence_path = None

    if role == "INSTRUCTOR":
        is_approved = False
        if evidence_file:
            filename = secure_filename(evidence_file.filename)
            evidence_path = os.path.join(UPLOAD_FOLDER, filename)
            evidence_file.save(evidence_path)

    u = User(username=username,
             password=password,
             email=email,
             fullName=fullname,
             role=role,
             evidence=evidence_path,
             is_approved=is_approved,
             balance=0)

    db.session.add(u)
    db.session.commit()

def load_course(id=None,coure_id=None,kw=None,page=1):
    query=Course.query

    if kw:
        return query.filter(Course.name.contains(kw))
    if id:
        return query.get(id)

    page_size=app.config["PAGE_SIZE"]
    start = (page - 1) * page_size
    query = query.slice(start,start+page_size)

    return query.all()

def get_user_by_id(id):
    return User.query.get(id)

def count_course():
    return Course.query.count()


def get_courses_by_user_id(user_id):
    return db.session.query(Course) \
        .join(Enrollment, Enrollment.course_id == Course.id) \
        .filter(Enrollment.student_id == user_id) \
        .all()


def get_lesson_by_course_id(course_id):

    if not course_id:
        return []

    lessons = Lesson.query.filter_by(course_id=course_id).all()
    return lessons
def get_user_by_email(email):
    return User.query.filter_by(email=email).first()

def get_user_by_username(username):
    return User.query.filter_by(username=username).first()
