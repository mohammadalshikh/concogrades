from flask import render_template, Blueprint, url_for, redirect
from flask_login import current_user, login_required

from .models import User, AssessmentCalculation, AssessmentDefinition, Announcement
from . import db

student = Blueprint('student', __name__, url_prefix='/student')

@student.route('/Home')
def home():
    return render_template("/student/Home.html")


@student.route('/Announcements')
def announcements():
    announcements = Announcement.query.order_by(Announcement.announcement_id.desc()).all()
    return render_template("/student/Announcements.html", announcements=announcements)


@student.route('/ClassList')
def classList():
    return render_template("/student/ClassList.html", students=User.getAllStudents())


@student.route('/StudentReportCard')
def studentReportCard():
    return render_template("/student/StudentReportCard.html")


@student.route('/ClassReportCard')
def classReportCard():
    dic = {}
    assessmentDefs = AssessmentDefinition.query.all()
    for assessmentDef in assessmentDefs:
        assessment_data = AssessmentCalculation.get_assessment_data(assessmentDef.assessment_id)
        if assessment_data.count == 0:
            dic[assessmentDef.assessment_id] = "Students: 0   Average: 0%    Standard Deviation: 0"
        else:
            dic[assessmentDef.assessment_id] = f"Students: {assessment_data.count}    Average: {round(assessment_data.average, 2)}%    Standard Deviation: {round(assessment_data.std_dev ** .5, 2)}"


    sum = 0
    sumOfSquares = 0
    count = 0
    for student in User.getAllStudents():
        average = student.user_average

        # skip student if average is nan
        if average != average: # cool way to check if average is nan
            continue
        sum += average
        sumOfSquares += average ** 2
        count += 1

    average = sum/count
    std_dev = ((sumOfSquares/count) - average ** 2) ** .5
    dic['total'] = f"Students: {count}    Average: {round(average, 2)}%    Standard Deviation: {round(std_dev, 2)}"
    
    return render_template("/student/ClassReportCard.html", subtitledict=dic, chartdata=AssessmentCalculation.get_graph_dict(10))


@student.route('/ContactUs')
def contactUs():
    return render_template("/student/ContactUs.html")


@student.before_request
@login_required
def before_request():
    if current_user.type != 'student':
        return redirect("/")