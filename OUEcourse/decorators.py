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

def get_embed_url(video_url):
    if not video_url:
        return None

    if "youtube.com/watch?v=" in video_url:
        video_id = video_url.split("watch?v=")[-1].split("&")[0]
        return f"https://www.youtube.com/embed/{video_id}"

    if "youtu.be/" in video_url:
        video_id = video_url.split("youtu.be/")[-1].split("?")[0]
        return f"https://www.youtube.com/embed/{video_id}"

    return video_url


