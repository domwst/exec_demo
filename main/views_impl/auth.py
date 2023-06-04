from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect
from django.views import View

User = get_user_model()


class SignupView(View):
    @staticmethod
    def post(req):
        username = req.POST.get("login", "")
        pwd1 = req.POST.get("password1", "")
        pwd2 = req.POST.get("password2", "")
        if not username or not pwd1 or not pwd2:
            return LoginView.get(req, err="Please fill all the fields", signup=True)
        if pwd1 != pwd2:
            return LoginView.get(req, err="Passwords don't match", signup=True)
        if User.objects.filter(username=username).exists():
            return LoginView.get(req, err="Such username already exists", signup=True)

        try:
            User.objects.create_user(username=username, password=pwd1)
        except ValidationError as e:
            return LoginView.get(req, err=e.message, signup=True)

        user = authenticate(username=username, password=pwd1)
        login(req, user)

        return redirect('index')


class LoginView(View):
    @staticmethod
    def get(req, err=None, signup=False):
        return render(req, "main/login.html", {"error_msg": err, "signup": signup})

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


class LogoutView(View):
    @staticmethod
    @login_required(login_url='login')
    def get(req):
        logout(req)
        return redirect("index")