from functools import wraps
from flask import request, redirect, url_for, abort, flash
from flask_login import current_user
from models import UserRole

def annonymous_user(f):
    @wraps(f)
    def decorated_func(*args,**kwargs):
        if current_user.is_authenticated:
            return redirect("/")
        return f(*args,**kwargs)

    return decorated_func

def admin_required(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return redirect(url_for("login_process", next=request.path))
        if getattr(current_user, "role", None) != UserRole.ADMIN:
            abort(403)
        return f(*args, **kwargs)
    return wrapper