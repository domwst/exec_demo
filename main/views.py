from django.contrib.auth import authenticate, login, logout
from django.core.exceptions import PermissionDenied, BadRequest
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.views import View
from django.utils import timezone
from main.models import Submission
from .exec_api import submit, getArtifact


class Login(View):
    def get(self, req, err=None):
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
    def get(self, req):
        if req.user.is_authenticated:
            logout(req)
        return redirect("index")


class Index(View):
    def get(self, req):
        return redirect(reverse('submissions'))


class SubmissionsView(View):
    def get(self, req, err=None):
        if req.user.is_anonymous:
            return redirect("login")
        submissions_to_check = req.user.submission_set.filter(nextCheck__lte=timezone.now())
        for subm in submissions_to_check:
            print(f"Trying to update {subm}")
            subm.tryUpdate()
        submissions = req.user.submission_set.order_by("-timestamp")
        return render(req, "main/submissions.html", {
            "submissions": submissions,
            "error_msg": err,
        })

    def post(self, req):
        if req.user.is_anonymous:
            return redirect("login")
        try:
            source = req.FILES["source"]
        except KeyError:
            return self.get(req, err="Please, select file")

        if len(source) > (64 << 10):
            return self.get(req, err="Your source should not exceed 64KB")

        user_submissions = Submission.objects.filter(user=req.user).order_by("-timestamp")
        if not req.user.is_staff and \
                user_submissions.count() != 0 and \
                timezone.now() - user_submissions[0].timestamp <= timezone.timedelta(seconds=10):
            return self.get(req, err="You are not allowed to submit more than once in 10 seconds")

        s = b''.join(c for c in source.chunks())
        inf = submit(s)
        subm = Submission(
            execId=inf['id'],
            sourceId=inf['src-id'],
            user=req.user,
        )
        subm.save()
        return redirect("submissions")


class SubmissionView(View):
    def get(self, req, id: int):
        if req.user.is_anonymous:
            return redirect("login")
        subm = get_object_or_404(Submission, pk=id)
        if not req.user.is_staff and subm.user != req.user:
            raise PermissionDenied("Not your submission")
        print(
            f"KEK: {subm.status}\n{Submission.CompilationStatus.FINISHED}\n{subm.status == Submission.CompilationStatus.FINISHED}")
        return render(req, 'main/submission.html', {
            'source': getArtifact(subm.sourceId),
            'subm': subm,
            'logs': getArtifact(subm.compilationResult.errorLog)
            if subm.status == Submission.CompilationStatus.FINISHED else None,
        })


class DownloadBinary(View):
    def get(self, req, id: int):
        if req.user.is_anonymous:
            return redirect("login")
        subm = get_object_or_404(Submission, pk=id)
        if not req.user.is_staff and subm.user != req.user:
            raise PermissionDenied("Not your submission")
        subm.tryUpdate()
        if subm.status != Submission.CompilationStatus.FINISHED:
            raise BadRequest("The submission is not yet finished")
        content = getArtifact(subm.compilationResult.binaryId)
        resp = HttpResponse(content, content_type="application/octet-stream")
        # resp["Content-Length"] = len(content)
        return resp
