from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied, BadRequest
from django.shortcuts import get_object_or_404, render, redirect
from django.urls import reverse
from django.utils.decorators import method_decorator
from django.views import View

from main.models_impl import ExecStatus, Run, OverallRunStatus, Submission
from main.tools.exec_api import execApi


class RunView(View):
    @method_decorator(login_required(login_url="login"))
    def get(self, req, id: int):
        run = get_object_or_404(Run, pk=id)
        run.tryUpdate()
        if run.submission.user != req.user and not req.user.is_staff:
            raise PermissionDenied("Not your run")

        stdout = stderr = result = None
        if run.execStatus == ExecStatus.FINISHED:
            stdout = execApi.getArtifact(run.runResult.stdoutId)
            stderr = execApi.getArtifact(run.runResult.stderrId)
            result = run.runResult

        return render(req, 'main/run.html', {
            'run': run,
            'stdout': stdout,
            'stderr': stderr,
            'runResult': result,
        })


class RunsView(View):
    @method_decorator(login_required(login_url="login"))
    def get(self, req):
        Run.tryUpdateAll()
        runs = Run.objects.filter(submission__user=req.user).order_by("-timestamp")
        return render(req, 'main/runs.html', {
            'runs': runs,
        })


class CreateRunView(View):
    @method_decorator(login_required(login_url="login"))
    def post(self, req, id: int):
        subm = get_object_or_404(Submission, pk=id)
        if subm.user != req.user and not req.user.is_staff:
            raise PermissionDenied("Not your submission")
        subm.tryUpdate()
        if subm.overallStatus() != OverallRunStatus.OK:
            raise BadRequest("The submission has not yet compiled, or compilation has failed")
        runId = execApi.run(subm.compilationResult.binaryId)
        run = Run(
            execId=runId,
            submission=subm,
        )
        run.save()
        return redirect(reverse('run', args=(run.pk,)))