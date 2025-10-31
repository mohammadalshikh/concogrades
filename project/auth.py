from flask import Blueprint, redirect, render_template, request, url_for, flash
from flask_login import current_user, login_user, logout_user
from werkzeug.security import check_password_hash
from werkzeug.urls import url_parse

from .models import User

auth = Blueprint('auth', __name__)


@auth.route('/', methods=['GET', 'POST'])
@auth.route('/Login', methods=['GET', 'POST'])
def login():
    # takes the user to the home page if they are already logged in
    if current_user.is_authenticated:
        return redirect(nextpage())
    
    if request.method == 'POST': # if the user has submitted the form
        id = request.form.get('id')
        password = request.form.get('password')
        remember = bool(request.form.get('remember-me'))
        

        if not id or not password: # empty input
            flash('Please enter your ID and password', 'alert alert-danger')
            return redirect('/Login')
        
        user = User.get(id)
        if user and check_password_hash(user.password, password): # check if user exists and password matches
            login_user(user, remember=remember)
            return redirect(nextpage())

        
        else:
            # one error for both cases because the user shouldn't know which one is wrong
            flash("Incorrect ID or password", 'alert alert-danger')
            return redirect('/Login')

    else: # GET request
        return render_template('/Login.html')


@auth.route("/Logout")
def logout():
    if current_user.is_authenticated:
        logout_user()
    return redirect(url_for("auth.login"))

def nextpage():
    next_page = request.args.get('next')
    if not next_page or url_parse(next_page).netloc != '':
        next_page = url_for(current_user.type + '.home')
    return next_page