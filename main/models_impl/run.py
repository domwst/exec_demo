from __future__ import annotations

import sys

from django.db import models
from django.utils import timezone

from main.tools import exec_api as execApi
from .abstract_run_result import AbstractRunResult, ExecStatus, OverallRunStatus
from .common import EXEC_ID_MAXLENGTH
from .submission import Submission


class RunResult(AbstractRunResult):
    stdoutId = models.TextField(max_length=EXEC_ID_MAXLENGTH)
    stderrId = models.TextField(max_length=EXEC_ID_MAXLENGTH)

    @staticmethod
    def FromExec(stats: execApi.RunOutcome) -> RunResult:
        return RunResult(
            **AbstractRunResult.FromExec(stats.statistics),
            stdoutId=stats.stdoutId,
            stderrId=stats.stderrId,
        )


class Run(models.Model):
    execId = models.TextField(max_length=EXEC_ID_MAXLENGTH)
    execStatus = models.TextField(max_length=2, choices=ExecStatus.choices, default=ExecStatus.ENQUEUED)
    runResult = models.ForeignKey(to=RunResult, on_delete=models.CASCADE, null=True, blank=True)
    nextCheck = models.DateTimeField(default=timezone.now, null=True)
    timestamp = models.DateTimeField(default=timezone.now)
    submission = models.ForeignKey(to=Submission, on_delete=models.CASCADE)

    def tryUpdate(self, force=False):
        if (self.nextCheck is None or self.nextCheck > timezone.now()) and not force:
            return
        print(f"Trying to update {self}")
        status = execApi.execApi.getRunStatus(self.execId)
        print(f"{status=}")
        self.nextCheck = timezone.now() + timezone.timedelta(milliseconds=500)
        self.execStatus = ExecStatus.FromExec(status.execStatus)

        if self.execStatus != ExecStatus.FINISHED:
            self.save()
            return

        self.nextCheck = None

        try:
            self.runResult = RunResult.FromExec(status.outcome)
            self.runResult.save()
        except Exception as e:
            print(f"Exception caught while trying to fetch result from exec: {e}", file=sys.stderr)
            self.execStatus = ExecStatus.ENQUEUED
            self.nextCheck = timezone.now() + timezone.timedelta(microseconds=500)

        self.save()

    @staticmethod
    def tryUpdateAll():
        for subm in Run.objects.filter(nextCheck__lt=timezone.now()):
            subm.tryUpdate()

    def overallStatus(self) -> OverallRunStatus:
        if self.execStatus != ExecStatus.FINISHED:
            return OverallRunStatus.FromExecStatus(self.execStatus)
        if self.runResult.verdict != AbstractRunResult.RunResult.OK:
            return OverallRunStatus.FromRunResult(AbstractRunResult.RunResult(self.runResult.verdict))
        if not self.runResult.exitStatus.isOk():
            return OverallRunStatus.RUNTIME_ERROR
        return OverallRunStatus.OK

