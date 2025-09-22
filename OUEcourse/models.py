from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from __init__ import app,db



# Enum cho role và status
from enum import Enum

class UserRole(Enum):
    STUDENT = "STUDENT"
    INSTRUCTOR = "INSTRUCTOR"
    ADMIN = "ADMIN"

class PaymentStatus(Enum):
    PENDING = "PENDING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"

# -------------------
# Bảng User
# -------------------
class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.BigInteger, primary_key=True,autoincrement=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    fullName = db.Column(db.String(120))
    role = db.Column(db.Enum(UserRole), default=UserRole.STUDENT)
    balance = db.Column(db.Float, default=0)
    evidence = db.Column(db.String(255))
    is_approved = db.Column(db.Boolean, default=False)

    courses = db.relationship("Course", backref="instructor", lazy=True)
    enrollments = db.relationship("Enrollment", backref="student", lazy=True)
    questions = db.relationship("Question", backref="author", lazy=True)

# -------------------
# Bảng Course
# -------------------
class Course(db.Model):
    __tablename__ = "courses"

    id = db.Column(db.BigInteger, primary_key=True,autoincrement=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    price = db.Column(db.Float, default=0)
    createdDate = db.Column(db.DateTime, default=datetime.utcnow)

    instructor_id = db.Column(db.BigInteger, db.ForeignKey("users.id"))

    lessons = db.relationship("Lesson", backref="course", lazy=True, cascade="all, delete-orphan")
    enrollments = db.relationship("Enrollment", backref="course", lazy=True)
    questions = db.relationship("Question", backref="course", lazy=True)

# -------------------
# Bảng Lesson
# -------------------
class Lesson(db.Model):
    __tablename__ = "lessons"

    id = db.Column(db.BigInteger, primary_key=True,autoincrement=True)
    title = db.Column(db.String(200), nullable=False)
    content = db.Column(db.Text)

    course_id = db.Column(db.BigInteger, db.ForeignKey("courses.id"))

# -------------------
# Bảng Enrollment
# -------------------
class Enrollment(db.Model):
    __tablename__ = "enrollments"

    id = db.Column(db.BigInteger, primary_key=True,autoincrement=True)
    enrollDate = db.Column(db.DateTime, default=datetime.utcnow)
    progress = db.Column(db.Float, default=0)

    student_id = db.Column(db.BigInteger, db.ForeignKey("users.id"))
    course_id = db.Column(db.BigInteger, db.ForeignKey("courses.id"))

    payments = db.relationship("Payment", backref="enrollment", lazy=True)

# -------------------
# Bảng Payment
# -------------------
class Payment(db.Model):
    __tablename__ = "payments"

    id = db.Column(db.BigInteger, primary_key=True,autoincrement=True)
    amount = db.Column(db.Float, nullable=False)
    paymentDate = db.Column(db.DateTime, default=datetime.utcnow)
    status = db.Column(db.Enum(PaymentStatus), default=PaymentStatus.PENDING)

    proof = db.Column(db.String(255))
    user_id = db.Column(db.BigInteger, db.ForeignKey("users.id"), nullable=True)  # thêm
    note = db.Column(db.String(255))  # nội dung CK
    enrollment_id = db.Column(db.BigInteger, db.ForeignKey("enrollments.id"))
    user = db.relationship("User", backref="payments")

# -------------------
# Bảng Question
# -------------------
class Question(db.Model):
    __tablename__ = "questions"

    id = db.Column(db.BigInteger, primary_key=True,autoincrement=True)
    content = db.Column(db.Text)
    createdDate = db.Column(db.DateTime, default=datetime.utcnow)

    course_id = db.Column(db.BigInteger, db.ForeignKey("courses.id"))
    author_id = db.Column(db.BigInteger, db.ForeignKey("users.id"))

    answers = db.relationship("Answer", backref="question", lazy=True)

# -------------------
# Bảng Answer
# -------------------
class Answer(db.Model):
    __tablename__ = "answers"

    id = db.Column(db.BigInteger, primary_key=True,autoincrement=True)
    content = db.Column(db.Text)
    createdDate = db.Column(db.DateTime, default=datetime.utcnow)

    question_id = db.Column(db.BigInteger, db.ForeignKey("questions.id"))



if __name__=='__main__':
    with app.app_context():
         db.create_all()