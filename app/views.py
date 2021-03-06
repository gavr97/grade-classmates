from django.shortcuts import render
from django.utils import timezone

from .models import *


def main_page(request):
    if request.user.is_authenticated:
        is_student = Student.objects.filter(user=request.user)
        if is_student:
            title = "Hello, User {}!".format(is_student.first().user)
            links_list = Link.objects.all().exclude(name="Students Login").exclude(name="Main")
        else:
            is_teacher = Teacher.objects.filter(user=request.user)
            if is_teacher:
                title = "Hello, Teacher {}!".format(is_teacher.first().user)
                links_list = Link.objects.all().exclude(name="Students Login").exclude(name="Main")
            else:
                title = "Hello, Admin {}!".format(request.user)
                links_list = Link.objects.all().exclude(name="Admin Login").exclude(name="Logout").exclude(name="Main")
    else:
        print("NOT AUTHENTICATED")
        title = "Hello, Guest!".format(request.user)
        links_list = Link.objects.all().exclude(
            name="Dashboard").exclude(name="Meeting 1 all results").exclude(name="Meeting 1 vote choice").exclude(
            name="Meeting 1 vote action").exclude(name="Logout").exclude(name="Main").exclude(
            name="Students Compare").exclude(name="Teachers Compare")
    context = {
        "title": title,
        "links_list": links_list
    }
    return render(request, 'app/main.html', context)


def index(request):
    time_now = timezone.now()
    context = {'time_now': time_now}
    return render(request, 'app/index.html', context)


def dashboard(request):
    current_user = request.user
    context = {'courses_enrolled': [],
               'first_name': current_user.first_name,
               'last_name': current_user.last_name,
               'email': current_user.email,
               'meeting_enrolled': []}

    students_enrolled = StudentEnrolled.objects.filter(student__user=current_user)
    for student_enrolled in students_enrolled:
        course_info = {'course_name': student_enrolled.course.name,
                       'start_date': student_enrolled.course.start_date,
                       'end_date': student_enrolled.course.end_date}
        context.get('courses_enrolled').append(course_info)

    students_attended = StudentAttends.objects.filter(student__user=current_user)
    for student_attended in students_attended:
        meeting = student_attended.meeting
        context.get('meeting_enrolled').append(meeting)

    meetings_list = sorted(context["meeting_enrolled"], key=lambda x: x.date)
    context["meeting_enrolled"] = meetings_list
    print(context["meeting_enrolled"])

    grade_actions = GradeAction.objects.all().filter(graded=current_user)
    context['positive_qualities'] = {}
    context['negative_qualities'] = {}

    def incr_average(merit, plus):
        last_count = merit[0]
        average = merit[1]
        merit[0] = last_count + 1
        merit[1] = round((average * last_count + plus) / merit[0], 2)

    # merit [count=0 ,average=0]

    for grade in grade_actions:
        merit = grade.merit
        if context['positive_qualities'].get(merit.name) == None:
            context['positive_qualities'][merit.name] = [0, 0]
        incr_average(context['positive_qualities'][merit.name], grade.grade)

    teachers_names = [teacher.user.username for teacher in Teacher.objects.all()]
    context["teachers_names"] = teachers_names
    return render(request, 'app/dashboard.html', context)


from .models import Meeting, GradeAction, TeacherAttends, StudentAttends
from django.shortcuts import get_object_or_404


def meeting_results(request, meeting_id):
    current_user = request.user
    meeting = get_object_or_404(Meeting, pk=meeting_id)

    teachers = TeacherAttends.objects.filter(meeting_id=meeting_id)  # TODO unique
    students = StudentAttends.objects.filter(meeting_id=meeting_id)

    tuples_teachers = [(participant.teacher.user.username, participant.teacher.user.id)
                       for participant in teachers]
    tuples_students = [(participant.student.user.username, participant.student.user.id)
                       for participant in students]

    tuples = [('', 1)] + tuples_teachers + tuples_students
    teachers_names = [teacher.teacher.user.username for teacher in teachers]
    students_names = [student.student.user.username for student in students]
    participants_names = teachers_names + students_names

    grades = GradeAction.objects.filter(meeting_id=meeting_id)
    mapping_from_username_to_index = {username: index
                                      for index, username in enumerate(participants_names)}

    table_of_grades = [[None] * (len(participants_names)) for _ in range(len(participants_names) + 1)]
    for grade in grades:
        try:
            index_grading = mapping_from_username_to_index[grade.grading.username]
            index_graded = mapping_from_username_to_index[grade.graded.username]
            table_of_grades[index_grading][index_graded + 1] = grade.grade
        except (IndexError, KeyError) as e:
            pass
            # TODO grade action from where grading or graded is not in meeting

    table_of_grades[0][0] = ""
    for i in range(len(participants_names)):
        table_of_grades[i][0] = participants_names[i]

    print(tuples)
    context = {
        'meeting': meeting,
        'grades': table_of_grades,
        'tuples': tuples
    }
    return render(request, 'app/vote_results_for_participant.html', context)


from django.contrib.auth.models import User
from .models import Merit


def meeting_vote_choice(request, meeting_id, graded_id):
    current_user = request.user
    meeting = get_object_or_404(Meeting, pk=meeting_id)
    graded = get_object_or_404(User, pk=graded_id)  # TODO Check that graded is from meeting_id
    merits = Merit.objects.all()

    context = {
        'meeting': meeting,
        'grading': current_user,
        'graded': graded,
        'merits': merits,
    }
    return render(request, 'app/voting.html', context)  # TODO Nikita


from django.http import HttpResponseRedirect
from django.urls import reverse


def meeting_vote_action(request, meeting_id, graded_id):
    current_user = request.user
    meeting = get_object_or_404(Meeting, pk=meeting_id)
    graded = get_object_or_404(User, pk=graded_id)
    try:
        grade = request.POST['overall_grade']
        print(grade)
        merits_ids = list(request.POST.keys())
        merits_ids.remove('overall_grade')
        merits_ids.remove('csrfmiddlewaretoken')
    except KeyError:
        merits = Merit.objects.all()
        merits_names_positive = list(
            map(lambda merit: merit.name,
                list(filter(lambda merit: merit.description == '+', merits))))
        merits_names_negative = list(
            map(lambda merit: merit.name,
                list(filter(lambda merit: merit.description == '-', merits))))
        context = {
            'meeting': meeting,
            'grading': current_user,
            'graded': graded,
            'merits_positive': merits_names_positive,
            'merits_negative': merits_names_negative
        }
        return render(request, 'app/voting.html', context)
    else:
        for merit_id in merits_ids:
            merit = Merit.objects.get(pk=merit_id)
            grade_action, created = GradeAction.objects.get_or_create(
                grading=current_user,
                graded=graded,
                grade=grade,
                merit=merit,
                meeting=meeting
            )
            grade_action.save()
        return HttpResponseRedirect(reverse('app:meeting_results', args=(meeting_id,)))


def users_results(request, users_type):
    merits = Merit.objects.all()
    merits_list = [''] + [merit.name for merit in merits]
    teachers_users = [teacher.user for teacher in Teacher.objects.all()]
    students_users = [student.user for student in Student.objects.all()]

    def incr_average(merit, plus):
        last_count = merit["count"]
        last_average = merit["average"]
        new_count = last_count + 1
        merit["average"] = round((last_average * last_count + plus) / new_count, 2)
        merit["count"] += 1

    if users_type == "students":
        students_or_teachers = [student.user for student in Student.objects.all()]
    elif users_type == "teachers":
        students_or_teachers = [teacher.user for teacher in Teacher.objects.all()]
    else:
        students_or_teachers = users_type

    if request.POST.get('filter_names') != None:
        students_or_teachers = request.POST['filter_names'].split('_')

    users_average_merits = {
        user.username: {} for user in students_or_teachers
    }

    if users_type != "students" and users_type != "teachers":
        user = User.objects.filter(username=users_type)
        grade_actions = GradeAction.objects.filter(grading=user)
    else:
        grade_actions = GradeAction.objects.all()

    for grade_action in grade_actions:
        user = grade_action.graded
        if users_type == "students":
            if user in teachers_users:
                # user is student
                continue
        elif users_type == "teachers":
            if user in students_users:
                # user is student
                continue

        grade = grade_action.grade
        merit = grade_action.merit
        if users_average_merits[user.username].get(merit.name) == None:
            users_average_merits[user.username][merit.name] = {"average": grade,
                                                               "count": 1}
        else:
            incr_average(users_average_merits[user.username][merit.name], grade)

    table_of_grades = [
        [None] * ((len(merits_list))) for _ in range(len(students_or_teachers))
    ]

    for user_average_merits in users_average_merits:
        for user_i, user in enumerate(students_or_teachers):
            for merit_i, merit in enumerate(merits):
                table_of_grades[user_i][merit_i + 1] = (
                    users_average_merits[user.username][merit.name]["average"],
                    users_average_merits[user.username][merit.name]["count"]
                )

    table_of_grades[0][0] = ""
    for i in range(len(students_or_teachers)):
        table_of_grades[i][0] = students_or_teachers[i]
    context = {
        'meeting': "Table_of_students" if users_type == "students" else "Table_of_teachers",
        'grades': table_of_grades,
        'tuples': merits_list,
        'user_type': users_type
    }
    return render(request, 'app/users_results.html', context)
