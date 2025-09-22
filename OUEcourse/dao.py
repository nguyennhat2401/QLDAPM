import hashlib
import os

from flask_login import current_user
from werkzeug.utils import secure_filename
from sqlalchemy import or_

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

    # Nếu là Instructor thì phải upload file và chờ duyệt
    if role == "INSTRUCTOR":
        is_approved = False  # Mặc định chờ duyệt

        if evidence_file and evidence_file.filename.strip():
            filename = secure_filename(evidence_file.filename)
            evidence_path = os.path.join(UPLOAD_FOLDER, filename)
            evidence_file.save(evidence_path)
        else:
            raise ValueError("Instructor phải upload minh chứng!")

    # Tạo user mới
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

    return u

def load_course(course_id=None, kw=None, page=1, page_size=None, id=None):
    """
    Trả về danh sách khóa học theo filter (course_id, kw) + phân trang.
    - Nếu truyền id: trả về 1 course (giữ tương thích cũ).
    """
    # Giữ tương thích với tham số cũ id
    if id:
        return Course.query.get(id)

    q = Course.query

    if course_id:
        q = q.filter(Course.id == course_id)

    if kw:
        like = f"%{kw.strip()}%"
        q = q.filter(
            or_(
                Course.title.ilike(like),
                Course.description.ilike(like)
            )
        )

    # Phân trang
    page = max(1, int(page or 1))
    if page_size is None:
        page_size = app.config.get("PAGE_SIZE", 12)

    items = (
        q.order_by(Course.createdDate.desc())
         .offset((page - 1) * page_size)
         .limit(page_size)
         .all()
    )
    return items
def get_user_by_id(id):
    return User.query.get(id)

def count_course(course_id=None, kw=None):
    """
    Đếm tổng số khóa học theo cùng filter với load_course để tính số trang.
    """
    q = Course.query

    if course_id:
        q = q.filter(Course.id == course_id)

    if kw:
        like = f"%{kw.strip()}%"
        q = q.filter(
            or_(
                Course.title.ilike(like),
                Course.description.ilike(like)
            )
        )

    return q.count()


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
