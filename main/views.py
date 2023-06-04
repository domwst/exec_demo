from django.shortcuts import redirect
from django.urls import reverse
from django.views import View
from .views_impl import (
    SubmissionView,
    SubmissionsView,
    RunView,
    RunsView,
    CreateRunView,
    LoginView,
    LogoutView,
    SignupView,
)


class Index(View):
    @staticmethod
    def get(_):
        return redirect(reverse('submissions'))
