import math
from datetime import datetime, date
from sqlalchemy import func, extract
from calendar import monthrange
from flask import render_template, request, redirect, flash, url_for, abort
from flask_login import login_user, logout_user, current_user, login_required
import os
import dao
from __init__ import app, Login, db
from dao import load_course, count_course, UPLOAD_FOLDER
from decorators import annonymous_user, admin_required
from models import (Enrollment, Course,
                    Lesson, UserRole, Payment, PaymentStatus, User)
from werkzeug.utils import secure_filename


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

    # Lấy lịch sử nạp tiền: payments có user_id và KHÔNG gắn enrollment (topup)
    topups = Payment.query \
        .filter(
        Payment.user_id == current_user.id,
        Payment.enrollment_id.is_(None)
    ) \
        .order_by(Payment.paymentDate.desc()) \
        .all()

    return render_template(
        "profile.html",
        user=current_user,
        user_courses=user_courses,
        teaching_courses=teaching_courses,
        topups=topups
    )

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
                if u.role == UserRole.ADMIN:
                    return redirect(url_for('admin_dashboard'))
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
@app.route("/courses/<int:course_id>/open")
def open_course(course_id):
    if not current_user.is_authenticated:
        return redirect(url_for('login_process', next=url_for('open_course', course_id=course_id)))

    course = Course.query.get_or_404(course_id)

    # Đã mua → vào thẳng khóa
    enrolled = Enrollment.query.filter_by(student_id=current_user.id, course_id=course_id).first()
    if enrolled:
        return redirect(url_for('course_detail', course_id=course_id))

    # Miễn phí → auto-enroll
    price = float(course.price or 0)
    if price == 0:
        e = Enrollment(student_id=current_user.id, course_id=course.id)
        db.session.add(e)
        db.session.commit()
        return redirect(url_for('course_detail', course_id=course_id))

    # Có phí → kiểm tra số dư
    if (current_user.balance or 0) < price:
        flash("Số dư không đủ. Vui lòng nạp tiền!", "danger")
        return redirect(url_for("topup"))

    # Trừ tiền & ghi nhận thanh toán thành công
    current_user.balance = (current_user.balance or 0) - price
    enroll = Enrollment(student_id=current_user.id, course_id=course.id)
    db.session.add(enroll)
    db.session.flush()  # lấy enroll.id

    pay = Payment(
        amount=price,
        status=PaymentStatus.SUCCESS,       # thanh toán thành công ngay vì trừ từ số dư
        enrollment_id=enroll.id,
        user_id=current_user.id,            # cần có cột user_id (như bạn đã dùng ở /topup)
        note=f"BUY-{course.id}-{current_user.id}"
    )
    db.session.add(pay)
    db.session.commit()

    flash("Mua khóa học thành công!", "success")
    return redirect(url_for('course_detail', course_id=course_id))

ALLOWED_PROOF_EXTS = {"png", "jpg", "jpeg", "pdf"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_PROOF_EXTS

@app.route("/topup", methods=["GET", "POST"])
@login_required
def topup():
    if request.method == "POST":
        amount = float(request.form.get("amount") or 0)
        proof_file = request.files.get("proof")
        proof_path = None

        if amount <= 0:
            flash("Số tiền nạp không hợp lệ!", "danger")
            return redirect(url_for("topup"))

        if proof_file and proof_file.filename and allowed_file(proof_file.filename):
            os.makedirs(app.config["PAYMENT_UPLOAD_FOLDER"], exist_ok=True)
            fname = secure_filename(f"{current_user.id}_{proof_file.filename}")
            save_path = os.path.join(app.config["PAYMENT_UPLOAD_FOLDER"], fname)
            proof_file.save(save_path)
            proof_path = save_path

        note_code = f"TOPUP-{current_user.id}-{int(datetime.utcnow().timestamp())}"

        pay = Payment(
            amount=amount,
            status=PaymentStatus.PENDING,
            user_id=current_user.id,
            note=note_code,
            proof=proof_path
        )
        db.session.add(pay)
        db.session.commit()

        flash("Đã gửi yêu cầu nạp tiền, vui lòng chờ duyệt!", "success")
        return redirect(url_for("profile"))

    bank_info = {
        "bank": "Vietcombank",
        "account_name": "CONG TY ECourse",
        "account_number": "0123456789",
        "note_format": f"TOPUP-{current_user.id}-<timestamp>"
    }
    return render_template("topup.html", bank_info=bank_info)



# ========= DASHBOARD =========
@app.route("/admin")
@admin_required
def admin_dashboard():
    # số liệu
    total_users = User.query.count()
    total_courses = Course.query.count()
    revenue = db.session.query(func.coalesce(func.sum(Payment.amount), 0.0))\
        .filter(Payment.status == PaymentStatus.SUCCESS,
                Payment.enrollment_id.isnot(None)).scalar()

    # biểu đồ nạp tiền theo ngày trong tháng hiện tại (chỉ topup đã duyệt)
    today = date.today()
    y, m = today.year, today.month
    days_in_month = monthrange(y, m)[1]

    # group theo ngày
    rows = db.session.query(
                func.date(Payment.paymentDate).label("d"),
                func.coalesce(func.sum(Payment.amount), 0.0)
            ).filter(
                Payment.user_id.isnot(None),           # là topup
                Payment.enrollment_id.is_(None),
                Payment.status == PaymentStatus.SUCCESS,
                extract('year', Payment.paymentDate) == y,
                extract('month', Payment.paymentDate) == m
            ).group_by(func.date(Payment.paymentDate))\
             .order_by(func.date(Payment.paymentDate)).all()

    # map ra mảng theo 1..days_in_month
    daily = { int(str(r[0])[-2:]): float(r[1]) for r in rows }  # key: day
    chart_labels = [str(i) for i in range(1, days_in_month+1)]
    chart_values = [daily.get(i, 0) for i in range(1, days_in_month+1)]

    return render_template("admin/dashboard.html",
                           total_users=total_users,
                           total_courses=total_courses,
                           revenue=revenue,
                           chart_labels=chart_labels,
                           chart_values=chart_values)

# ========= LIST INSTRUCTORS =========
@app.route("/admin/instructors")
@admin_required
def admin_instructors():
    instructors = User.query.filter(User.role == UserRole.INSTRUCTOR)\
                            .order_by(User.id.desc()).all()
    return render_template("admin/instructors.html", instructors=instructors)


# ========= APPROVALS (2 tab con) =========
@app.route("/admin/approvals")
@admin_required
def admin_approvals():
    pending_instructors = User.query.filter(
        User.role == UserRole.INSTRUCTOR, User.is_approved == False
    ).order_by(User.id.desc()).all()

    pending_topups = Payment.query.filter(
        Payment.user_id.isnot(None),
        Payment.enrollment_id.is_(None),
        Payment.status == PaymentStatus.PENDING
    ).order_by(Payment.paymentDate.desc()).all()

    return render_template("admin/approvals.html",
                           pending_instructors=pending_instructors,
                           pending_topups=pending_topups)
@app.route("/admin/instructors/pending")
@admin_required
def admin_instructors_pending():
    instructors = User.query.filter(
        User.role == UserRole.INSTRUCTOR, User.is_approved == False
    ).order_by(User.id.desc()).all()
    return render_template("admin/instructors_pending.html", instructors=instructors)

@app.route("/admin/instructors/<int:user_id>/approve", methods=["POST"])
@admin_required
def admin_approve_instructor(user_id):
    u = User.query.get_or_404(user_id)
    if u.role != UserRole.INSTRUCTOR:
        abort(400)
    u.is_approved = True
    db.session.commit()
    flash("Đã duyệt giảng viên.", "success")
    return redirect(url_for("admin_instructors_pending"))

@app.route("/admin/instructors/<int:user_id>/reject", methods=["POST"])
@admin_required
def admin_reject_instructor(user_id):
    u = User.query.get_or_404(user_id)
    if u.role != UserRole.INSTRUCTOR:
        abort(400)
    u.is_approved = False
    db.session.commit()
    flash("Đã cập nhật trạng thái (từ chối).", "warning")
    return redirect(url_for("admin_instructors_pending"))

# ========================
# ADMIN: Courses
# ========================
@app.route("/admin/courses")
@admin_required
def admin_courses():
    courses = Course.query.order_by(Course.id.desc()).all()
    return render_template("admin/courses.html", courses=courses)

@app.route("/admin/courses/<int:course_id>/delete", methods=["POST"])
@admin_required
def admin_delete_course(course_id):
    c = Course.query.get_or_404(course_id)
    db.session.delete(c)   # cascade xóa lessons
    db.session.commit()
    flash("Đã xóa khóa học.", "success")
    return redirect(url_for("admin_courses"))

# ========================
# ADMIN: Duyệt nạp tiền (Topup)
# ========================
@app.route("/admin/topups")
@admin_required
def admin_topups():
    page = int(request.args.get("page", 1))
    per_page = 15

    q = Payment.query.filter(
        Payment.user_id.isnot(None),  # là topup
        Payment.enrollment_id.is_(None)
    ).order_by(Payment.paymentDate.desc())

    total = q.count()
    pages = math.ceil(total / per_page) if total else 1
    topups = q.offset((page - 1) * per_page).limit(per_page).all()

    # tổng nạp đã duyệt (SUCCESS)
    topup_revenue = db.session.query(func.coalesce(func.sum(Payment.amount), 0.0)).filter(
        Payment.user_id.isnot(None),
        Payment.enrollment_id.is_(None),
        Payment.status == PaymentStatus.SUCCESS
    ).scalar()

    return render_template(
        "admin/topups.html",
        topups=topups,
        page=page,
        pages=pages,
        total=total,
        topup_revenue=topup_revenue
    )
@app.route("/admin/topups/<int:payment_id>/approve", methods=["POST"])
@admin_required
def admin_approve_topup(payment_id):
    p = Payment.query.get_or_404(payment_id)
    if p.enrollment_id is not None:  # không phải topup
        abort(400)
    if p.status == PaymentStatus.SUCCESS:
        flash("Giao dịch đã duyệt trước đó.", "info")
        return redirect(url_for("admin_topups"))

    user = User.query.get_or_404(p.user_id)
    user.balance = (user.balance or 0) + (p.amount or 0)
    p.status = PaymentStatus.SUCCESS
    db.session.commit()
    flash("Đã duyệt nạp tiền và cộng vào số dư.", "success")
    return redirect(url_for("admin_topups"))

@app.route("/admin/topups/<int:payment_id>/reject", methods=["POST"])
@admin_required
def admin_reject_topup(payment_id):
    p = Payment.query.get_or_404(payment_id)
    if p.enrollment_id is not None:
        abort(400)
    p.status = PaymentStatus.FAILED
    db.session.commit()
    flash("Đã từ chối giao dịch nạp tiền.", "warning")
    return redirect(url_for("admin_topups"))

if __name__ == '__main__':
    app.run(debug=True)
