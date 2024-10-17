from django.http import HttpResponse

def index(request):
    return HttpResponse("Welcome to the Task Management API")