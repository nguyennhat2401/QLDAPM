from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from urllib.parse import quote


app=Flask(__name__)
app.secret_key='KJHKHJKYGJYGBJNMK@^*&$^*#@!#*(>?<'
app.config["SQLALCHEMY_DATABASE_URI"] = "mysql+pymysql://root:%s@localhost/ecoursedb?charset=utf8mb4" % quote("240104")
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = True
app.config['PAGE_SIZE']=4


db=SQLAlchemy(app=app)
Login=LoginManager(app=app)