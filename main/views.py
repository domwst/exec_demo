from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from django.urls import reverse
from django.views import View
from .views_impl.submissions import SubmissionView, SubmissionsView
from .views_impl.runs import RunView, RunsView, CreateRunView


class Login(View):
    @staticmethod
    def get(req, err=None):
        return render(req, "main/login.html", {"error_msg": err})

    def post(self, req):
        try:
            username = req.POST["login"]
            password = req.POST["password"]
        except KeyError:
            return self.get(req, err="Please enter login and password")
        user = authenticate(username=username, password=password)
        if user is None:
            return self.get(req, err="Incorrect login or password")
        login(req, user)
        return redirect("index")


class Logout(View):
    @staticmethod
    @login_required(login_url='login')
    def get(req):
        logout(req)
        return redirect("index")


class Index(View):
    @staticmethod
    def get(_):
        return redirect(reverse('submissions'))
