from flask import render_template, request, redirect, url_for, flash
#from flask_login import login_user, login_required, current_user, logout_user
from werkzeug.security import check_password_hash
import datetime
from . import app
from .database import session

@app.route("/")
def entries ():
    return render_template("test.html")