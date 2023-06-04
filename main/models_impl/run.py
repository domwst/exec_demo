from __future__ import annotations

from django.db import models

from main.tools import exec_api as execApi
from .abstract_run_result import AbstractRunResult
from .absrtract_exec_run import AbstractExecRun
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


class Run(AbstractExecRun):
    runResult = models.ForeignKey(to=RunResult, on_delete=models.CASCADE, null=True, blank=True)
    submission = models.ForeignKey(to=Submission, on_delete=models.CASCADE)

    def _getResult(self) -> AbstractRunResult:
        return self.runResult

    def _updateFromOutcome(self, outcome):
        self.runResult = RunResult.FromExec(outcome)
        self.runResult.save()

    @staticmethod
    def _fetchStatusFromExec(id: str):
        return execApi.execApi.getRunStatus(id)
