from flask import render_template, request, redirect, Blueprint, flash, url_for
from flask_login import current_user, login_required
from datetime import datetime

from .models import User, AssessmentCalculation, AssessmentDefinition, Announcement
from . import db, is_number

admin = Blueprint('admin', __name__, url_prefix='/admin', template_folder="templates/admin")

@admin.route('/Home')
def home():
    return render_template("/Home.html")


@admin.route('/Announcements', methods=['GET', 'POST'])
def announcements():
    if request.method == 'POST':
        if "announcement" in request.form:
            date = request.form.get('date')
            date = datetime.strptime(date, '%Y-%m-%d')
            announcement = request.form.get('announcement')
            Announcement(announcement, date)
        else: # Delete announcements
            Announcement.query.filter(Announcement.announcement_id.in_(request.form)).delete()
            db.session.commit()
        return redirect("/admin/Announcements")
    else:
        announcements = Announcement.query.order_by(Announcement.announcement_id.desc()).all()
        return render_template("/Announcements.html", announcements=announcements)


@admin.route('/ClassList', methods=['GET', 'POST'])
def classList():
    if request.method == 'POST':
        students = User.getAllStudents()
        assessmentDefs = AssessmentDefinition.query.all()
        for student in students:
            if bool(request.form.get(str(student.id) + "|" + "delete")):
                User.query.filter_by(id=student.id).delete()
                AssessmentCalculation.query.filter_by(user_id=student.id).delete()
                continue
            
            fname = request.form.get(str(student.id) + "|" + "fname")
            if fname:
                student.fname = fname
            lname = request.form.get(str(student.id) + "|" + "lname")
            if lname:
                student.lname = lname

            for assessmentDef in assessmentDefs:
                assessmentScore = request.form.get(str(student.id) + "|" + assessmentDef.assessment_id)
                if assessmentScore:
                    if not is_number(assessmentScore):
                        continue
                    assessmentScore = float(assessmentScore)
                    if assessmentScore < 0 or assessmentScore > 100:
                        continue
                    AssessmentCalculation(student.id, assessmentDef.assessment_id, round(assessmentScore, 2))
                else:
                    AssessmentCalculation.query.filter_by(user_id=student.id, assessment_id=assessmentDef.assessment_id).delete()
        db.session.commit()
        return redirect("/admin/ClassList")
    else:    
        assessmentDefs = AssessmentDefinition.query.all()
        students = User.getAllStudents()
        return render_template("/ClassList.html", students=students, assessmentDefs=assessmentDefs)


@admin.route('/EnrollStudent', methods=['GET', 'POST'])
def enrollStudent():
    if request.method == 'POST':
        # if there is a file in the request
        if request.form.get('submit') == "Upload Text File":
            file = request.files['file']
            if (file.filename == ''):
                flash('No file selected', 'error')
                return redirect(url_for('.enrollStudent'))
            if ('.' not in file.filename) or (file.filename.split('.')[-1] != 'txt'):
                flash('Invalid file.', 'error')
                return redirect(url_for('.enrollStudent'))

            added = 0
            modified = 0
            data = file.read().decode("utf-8")
            for line in data.splitlines():
                line = line.split()
                if len(line) != 4:
                    continue
                if not line[0].isdigit():  # if the id is not a number
                    continue

                user = User.get(line[0])
                if user:
                    if user.type == "admin":  # skip if user already exists and is admin
                        continue
                    user.modifyUser(line[1], line[2], line[3], "student")
                    modified += 1
                else:
                    User(id=line[0], fname=line[1], lname=line[2],
                         password=line[3], type="student")
                    added += 1
            db.session.commit()
            flash(f"{added} students added", "success")
            flash(f"{modified} students modified", "success")
            return redirect(url_for('.enrollStudent'))

        else:  # manual submission
            id = request.form.get('id')
            fname = request.form.get('fname')
            lname = request.form.get('lname')
            password = request.form.get('password')
            user = User.get(id)

            if user and user.type == 'admin':  # admin accounts need to be created manually
                flash("This ID belongs to an admin account. Please use a different ID", "error")
                return redirect(url_for('.enrollStudent'))

            elif user and user.type == 'student':  # modifies the existing student account
                user.modifyUser(fname, lname, password, 'student')
                insertAssessments(user.id)
                flash("Student account modified", "success")
                return redirect(url_for('.enrollStudent'))

            else:  # creates a new student account
                user = User(id=id, fname=fname, lname=lname,
                            password=password, type='student')
                insertAssessments(user.id)
                flash("Student successfully enrolled", "success")
                return redirect(url_for('.enrollStudent'))

    else:  # GET request
        return render_template("/EnrollStudent.html")


@admin.route('/StudentReportCard')
def studentReportCard():
    students = User.getAllStudents()
    return render_template("/StudentReportCard.html", students=students)


@admin.route('/StudentReportCard/<student_id>')
def currentStudentReportCard(student_id=None):
    current_student = User.get(student_id)
    if not current_student:
        return redirect(url_for('.studentReportCard'))
    return render_template("/StudentReportCard.html", current_student=current_student)


@admin.route('/ClassReportCard')
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

    if count == 0:
        dic['total'] = "Students: 0    Average: 0%    Standard Deviation: 0"
    else:
        average = sum/count
        std_dev = ((sumOfSquares/count) - average ** 2) ** .5
        dic['total'] = f"Students: {count}    Average: {round(average, 2)}%    Standard Deviation: {round(std_dev, 2)}"
    
    return render_template("/ClassReportCard.html", subtitledict=dic, chartdata=AssessmentCalculation.get_graph_dict(10))

@admin.route('/ContactUs')
def contactUs():
    return render_template("/ContactUs.html")


# Gets all the assessments from the form and inserts them into the db
def insertAssessments(user_id):
    assessments = AssessmentDefinition.query.all()
    for assessment in assessments:
        formValue = request.form.get(assessment.assessment_id)
        if formValue and is_number(formValue):
            formValue = float(formValue)
            if formValue < 0 or formValue > 100:
                continue
            AssessmentCalculation(user_id, assessment.assessment_id, round(formValue, 2))
            db.session.commit()

# This basically checks that the user is logged in and is an admin otherwise returns them to the right page
@admin.before_request
@login_required
def before_request():
    if current_user.type != 'admin':
        return redirect("/")
