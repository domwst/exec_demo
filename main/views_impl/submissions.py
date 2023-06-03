from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, BadRequest
from django.http import HttpResponse
from django.shortcuts import render, redirect, get_object_or_404
from django.utils.decorators import method_decorator
from django.views import View

from main.models_impl.abstract_run_result import ExecStatus, OverallRunStatus
from main.models_impl.submission import Submission
from main.tools.exec_api import execApi


class SubmissionsView(View):
    @staticmethod
    @login_required(login_url='login')
    def get(req, err=None):
        Submission.tryUpdateAll()
        submissions = req.user.submission_set.order_by("-timestamp")
        return render(req, "main/submissions.html", {
            "submissions": submissions,
            "error_msg": err,
        })

    @method_decorator(login_required(login_url='login'))
    def post(self, req):
        try:
            source = req.FILES["source"]
        except KeyError:
            return self.get(req, err="Please, select file")

        if len(source) > (64 << 10):
            return self.get(req, err="Your source should not exceed 64KB")

        # user_submissions = Submission.objects.filter(user=req.user).order_by("-timestamp")
        # if not req.user.is_staff and \
        #         user_submissions.exists() and \
        #         timezone.now() - user_submissions.first().timestamp <= timezone.timedelta(seconds=10):
        #     return self.get(req, err="You are not allowed to submit more than once in 10 seconds")

        s = b''.join(c for c in source.chunks())
        inf = execApi.submit(s)
        subm = Submission(
            execId=inf['id'],
            sourceId=inf['src-id'],
            user=req.user,
        )
        subm.save()
        return redirect("submissions")


class SubmissionView(View):
    @staticmethod
    @login_required(login_url='login')
    def get(req, id: int):
        subm = get_object_or_404(Submission, pk=id)
        if not req.user.is_staff and subm.user != req.user:
            raise PermissionDenied("Not your submission")
        logs = runs = None
        if subm.execStatus == ExecStatus.FINISHED:
            logs = execApi.getArtifact(subm.compilationResult.errorLog)
            runs = subm.run_set.order_by("-timestamp")
        return render(req, 'main/submission.html', {
            'source': execApi.getArtifact(subm.sourceId),
            'subm': subm,
            'runs': runs,
            'logs': logs,
        })
