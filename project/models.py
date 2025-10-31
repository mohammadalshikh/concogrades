from . import db
from flask_login import UserMixin
from werkzeug.security import generate_password_hash
from sqlalchemy import func, cast


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fname = db.Column(db.String)
    lname = db.Column(db.String)
    password = db.Column(db.String)
    type = db.Column(db.String)
    assessments = db.relationship("AssessmentCalculation", backref="user")

    def __init__(self, id, fname, lname, password, type):
        self.id = id
        self.fname = fname
        self.lname = lname
        self.password = generate_password_hash(password)
        self.type = type
        db.session.merge(self)
        db.session.commit()

    def modifyUser(self, fname, lname, password, type):
        self.fname = fname
        self.lname = lname
        self.password = generate_password_hash(password)
        self.type = type
        db.session.commit()

 
    @staticmethod
    def getAllStudents():
        return User.query.filter_by(type="student").all()

    def get(id):
        return User.query.get(id)

    # returns a dict with {assessment_id : score} with average 
    def get_grades(self):
        assessment_defs = AssessmentDefinition.query.all()
        dic = {}
        for assessment_def in assessment_defs:
            assessment_id = assessment_def.assessment_id
            dic[assessment_id] = None
            for user_assessment in self.assessments:
                if user_assessment.assessment_id == assessment_id:
                    dic[assessment_id] = user_assessment.assessment_score
        dic['average'] = self.user_average
        return dic

    @property
    def user_average(self):
        user_id = self.id
        numerator = 0
        denom = 100

        percentage_assessments = AssessmentDefinition.query.filter_by(
            assessment_weight_type="percentage"
        ).all()
        assessments_by_percentage_total = sum(assessment.assessment_weight for assessment in percentage_assessments)

        relative_assessments = AssessmentDefinition.query.filter_by(
            assessment_weight_type="relative"
        ).all()
        relative_assessments_total_weight = sum(assessment.assessment_weight for assessment in relative_assessments)

        total_relative_percentage = 100 - (assessments_by_percentage_total)

        for asses in percentage_assessments:
            current_assessment = AssessmentCalculation.query.get((user_id, asses.assessment_id))
            if current_assessment:
                numerator += asses.assessment_weight * current_assessment.assessment_score / 100
            else:
                denom -= asses.assessment_weight
        
        for asses in relative_assessments:
            current_assessment = AssessmentCalculation.query.get((user_id, asses.assessment_id))
            if current_assessment:
                numerator += current_assessment.assessment_score * (asses.assessment_weight/relative_assessments_total_weight) * total_relative_percentage / (100)
            else:
                denom -= (asses.assessment_weight / relative_assessments_total_weight) * total_relative_percentage

        if round(denom, 2) == 0:
            return float("nan")
        return round(numerator / denom * 100, 2)

class AssessmentDefinition(db.Model):
    assessment_id = db.Column(db.String, primary_key=True)
    assessment_name = db.Column(db.String)
    assessment_weight = db.Column(db.Integer)
    assessment_weight_type = db.Column(db.String)

    def __init__(self, assessment_id, assessment_name, assessment_weight, assessment_weight_type):
        self.assessment_id = assessment_id
        self.assessment_name = assessment_name
        self.assessment_weight = assessment_weight
        self.assessment_weight_type = assessment_weight_type


class AssessmentCalculation(db.Model):
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    assessment_id = db.Column(db.String, db.ForeignKey(
        'assessment_definition.assessment_id'), primary_key=True)
    assessment_score = db.Column(db.Float())

    def __init__(self, user_id, assessment_id, assessment_score):
        self.user_id = user_id
        self.assessment_id = assessment_id
        self.assessment_score = assessment_score
        db.session.merge(self)
        db.session.commit()

    @staticmethod
    def get_graph_dict(increment):
        columns = int((100/increment)+1)

        # for some reason this is the only way it would work and I do not have the energy to understand it
        increment_divided_by_2 = int(increment/2) 

        dic = {}
        assessments_defs = AssessmentDefinition.query.all()

        for assessment_def in assessments_defs:
            id = assessment_def.assessment_id
            dic[id] = []
            for i in range(columns):
                dic[id].append(AssessmentCalculation.query.filter(
                    cast((AssessmentCalculation.assessment_score + increment_divided_by_2)/increment, db.Integer) == i,
                    AssessmentCalculation.assessment_id == assessment_def.assessment_id
                    ).count())
        

        students = User.getAllStudents()
        dic["total"] = [0] * columns
        for student in students:
            average = student.user_average
            if average != average: # this checks if average is nan
                continue
            dic["total"][int((average/increment)+0.5)] += 1

        return dic

    @staticmethod
    def get_assessment_data(assessment_id):
        result = AssessmentCalculation.query.with_entities(
            func.avg(AssessmentCalculation.assessment_score).label('average'),
            func.count(AssessmentCalculation.assessment_score).label('count'),

            # standard deviation, need to get the sqrt first.
            (func.avg(AssessmentCalculation.assessment_score*AssessmentCalculation.assessment_score) \
                - func.avg(AssessmentCalculation.assessment_score) * \
                    func.avg(AssessmentCalculation.assessment_score)).label('std_dev'),
        ).filter(
            AssessmentCalculation.assessment_id == assessment_id
        ).first()

        return result
        


class Announcement(db.Model):
    announcement_id = db.Column(db.Integer, primary_key=True)
    announcement_text = db.Column(db.Text)
    announcement_date = db.Column(db.DateTime)

    def __init__(self, text, date):
        self.announcement_text = text
        self.announcement_date = date
        db.session.add(self)
        db.session.commit()

    @property
    def formatted_announcement_date(self):
        return self.announcement_date.strftime("%d %B, %Y")