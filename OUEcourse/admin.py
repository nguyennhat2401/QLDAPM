# @app.route("/approve/<int:user_id>")
# def approve_instructor(user_id):
#     user = User.query.get(user_id)
#     if user and user.role == "INSTRUCTOR":
#         user.is_approved = True
#         db.session.commit()
#     return redirect("/admin/instructors")
