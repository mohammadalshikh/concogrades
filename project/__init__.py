from secrets import token_hex

from flask import Flask
from flask_login import LoginManager
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()  # used for database connection

from .models import User, AssessmentDefinition, AssessmentCalculation

def create_app():
    app = Flask(__name__)

    app.secret_key = token_hex()  # generates random token
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///data.db"
    # app.config['EXPLAIN_TEMPLATE_LOADING'] = True # debug template errors
    app.config['TEMPLATES_AUTO_RELOAD'] = True # reload templates on every change
    app.jinja_env.auto_reload = True

    db.init_app(app)

    login_manager = LoginManager()
    login_manager.login_view = "auth.login" # redirects to login page if not logged in
    login_manager.login_message = "Please login to view this page."
    login_manager.login_message_category = "alert alert-danger" # bootstrap styling for the login_message
    login_manager.init_app(app)

    # create a user loader function takes userid and returns User
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(user_id)

    
    with app.app_context():
        db.create_all()  # create database tables
        # default admin user
        User(123, "Anthony", "Andreoli", "123", "admin")

        assessments_seeding = {
            "a1": ("a1", "A1", 1, "relative"),
            "a2": ("a2", "A2", 1, "relative"),
            "a3": ("a3", "A3", 1, "relative"),
            "midterm": ("midterm", "Midterm", 30, "percentage"),
            "final": ("final", "Final", 50, "percentage")
        }

        list(map(lambda x: db.session.merge(AssessmentDefinition(*assessments_seeding[x])), assessments_seeding.keys()))

        db.session.commit()

    # blueprints for the app
    from .auth import auth as auth_blueprint
    from .admin import admin as admin_blueprint
    from .student import student as student_blueprint
    app.register_blueprint(auth_blueprint)
    app.register_blueprint(admin_blueprint)
    app.register_blueprint(student_blueprint)

    @app.template_global()
    def getGrade(user_id, assessment_id):
        assessment = AssessmentCalculation.query.get((user_id, assessment_id))
        if assessment:
            score = ('%f' % assessment.assessment_score).rstrip('0').rstrip('.')
            return score
        else:
            return ""


    return app

def is_number(s):
    try:
        float(s)
        return True
    except ValueError:
        return False