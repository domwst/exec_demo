from __future__ import annotations

from django.db import models
from django.conf import settings
from django.utils import timezone
from main.tools import exec_api as execApi
from .abstract_run_result import AbstractRunResult, ExecStatus, OverallRunStatus
from .absrtract_exec_run import AbstractExecRun
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


class Submission(AbstractExecRun):
    sourceId = models.CharField(max_length=EXEC_ID_MAXLENGTH)
    compilationResult = models.ForeignKey(to=CompilationResult, on_delete=models.CASCADE, null=True, blank=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def _updateFromOutcome(self, outcome):
        self.compilationResult = CompilationResult.FromExec(outcome)
        self.compilationResult.save()

    @staticmethod
    def _fetchStatusFromExec(id: str):
        return execApi.execApi.getSubmissionStatus(id)

    def _getResult(self) -> AbstractRunResult:
        return self.compilationResult

    def overallCompilationStatus(self) -> str:
        status = self.overallStatus()
        if status == OverallRunStatus.RUNTIME_ERROR:
            return 'CE'
        return status
