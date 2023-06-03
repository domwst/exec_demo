from __future__ import annotations

from django.db import models
from django.conf import settings
from django.utils import timezone
from main.tools import exec_api as execApi
from .abstract_run_result import AbstractRunResult, ExecStatus, OverallRunStatus
from .common import EXEC_ID_MAXLENGTH


class CompilationResult(AbstractRunResult):
    errorLog = models.CharField(max_length=EXEC_ID_MAXLENGTH)
    binaryId = models.CharField(max_length=EXEC_ID_MAXLENGTH, null=True)

    @staticmethod
    def FromExec(outcome: execApi.CompilationOutcome) -> CompilationResult:
        r = CompilationResult(
            **AbstractRunResult.FromExec(outcome.statistics),
            errorLog=outcome.errorLogId,
            binaryId=outcome.binaryId,
        )
        return r


class Submission(models.Model):
    execId = models.CharField(max_length=EXEC_ID_MAXLENGTH)
    execStatus = models.CharField(
        max_length=2,
        choices=ExecStatus.choices,
        default=ExecStatus.ENQUEUED,
    )
    sourceId = models.CharField(max_length=EXEC_ID_MAXLENGTH)
    nextCheck = models.DateTimeField(default=timezone.now, null=True)
    compilationResult = models.ForeignKey(to=CompilationResult, on_delete=models.CASCADE, null=True, blank=True)
    timestamp = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def tryUpdate(self, force=False):
        if (self.nextCheck is None or self.nextCheck > timezone.now()) and not force:
            return
        print(f"Trying to update {self}")
        status = execApi.execApi.getSubmissionStatus(self.execId)
        print(f"{status=}")
        self.nextCheck = timezone.now() + timezone.timedelta(milliseconds=500)
        self.execStatus = ExecStatus.FromExec(status.execStatus)

        if self.execStatus != ExecStatus.FINISHED:
            self.save()
            return

        self.nextCheck = None

        try:
            self.compilationResult = CompilationResult.FromExec(status.outcome)
            self.compilationResult.save()
        except Exception as e:
            print(f"Exception caught while trying to fetch result from exec: {e}")
            self.execStatus = ExecStatus.ENQUEUED
            self.nextCheck = timezone.now() + timezone.timedelta(microseconds=500)

        self.save()

    @staticmethod
    def tryUpdateAll():
        for subm in Submission.objects.filter(nextCheck__lt=timezone.now()):
            subm.tryUpdate()

    def overallStatus(self) -> OverallRunStatus:
        if self.execStatus != ExecStatus.FINISHED:
            return OverallRunStatus.FromExecStatus(self.execStatus)
        if self.compilationResult.verdict != AbstractRunResult.RunResult.OK:
            return OverallRunStatus.FromRunResult(AbstractRunResult.RunResult(self.compilationResult.verdict))
        if not self.compilationResult.exitStatus.isOk():
            return OverallRunStatus.RUNTIME_ERROR
        return OverallRunStatus.OK

    def overallCompilationStatus(self) -> str:
        status = self.overallStatus()
        if status == OverallRunStatus.RUNTIME_ERROR:
            return 'CE'
        return status
