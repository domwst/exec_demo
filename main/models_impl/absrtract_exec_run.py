from abc import abstractmethod
from django.db import models
from django.utils import timezone

from .abstract_run_result import ExecStatus, OverallRunStatus, AbstractRunResult
from .abc_model_meta import ABCModelMeta
from .common import EXEC_ID_MAXLENGTH


class AbstractExecRun(models.Model, metaclass=ABCModelMeta):
    execId = models.TextField(max_length=EXEC_ID_MAXLENGTH)
    execStatus = models.TextField(max_length=2, choices=ExecStatus.choices, default=ExecStatus.ENQUEUED)
    nextCheck = models.DateTimeField(default=timezone.now, null=True)
    timestamp = models.DateTimeField(default=timezone.now)

    @abstractmethod
    def _updateFromOutcome(self, outcome):
        pass

    @staticmethod
    @abstractmethod
    def _fetchStatusFromExec(id: str):
        pass

    @abstractmethod
    def _getResult(self) -> AbstractRunResult:
        pass

    def tryUpdate(self, force=False):
        if (self.nextCheck is None or self.nextCheck > timezone.now()) and not force:
            return
        print(f"Trying to update {self}")
        status = self._fetchStatusFromExec(self.execId)
        print(f"{status=}")
        self.nextCheck = timezone.now() + timezone.timedelta(milliseconds=500)
        self.execStatus = ExecStatus.FromExec(status.execStatus)

        if self.execStatus != ExecStatus.FINISHED:
            self.save()
            return

        self.nextCheck = None

        try:
            self._updateFromOutcome(status.outcome)
        except Exception as e:
            print(f"Exception caught while trying to fetch result from exec: {e}", file=sys.stderr)
            self.execStatus = ExecStatus.ENQUEUED
            self.nextCheck = timezone.now() + timezone.timedelta(microseconds=500)

        self.save()

    @classmethod
    def tryUpdateAll(cls):
        for subm in cls.objects.filter(nextCheck__lt=timezone.now()):
            subm.tryUpdate()

    def overallStatus(self) -> OverallRunStatus:
        if self.execStatus != ExecStatus.FINISHED:
            return OverallRunStatus.FromExecStatus(self.execStatus)
        if self._getResult().verdict != AbstractRunResult.RunResult.OK:
            return OverallRunStatus.FromRunResult(AbstractRunResult.RunResult(self._getResult().verdict))
        if not self._getResult().exitStatus.isOk():
            return OverallRunStatus.RUNTIME_ERROR
        return OverallRunStatus.OK

    class Meta:
        abstract = True
