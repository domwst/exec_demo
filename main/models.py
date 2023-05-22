from django.db import models
from django.utils.translation import gettext_lazy as _
from composite_field import CompositeField
from django.conf import settings
from django.utils import timezone
from .exec_api import getSubmissionStatus

EXEC_ID_MAXLENGTH = 64


class AbstractRunResult(models.Model):
    class RunResult(models.TextChoices):
        OK = "OK", _("Ok")
        WALL_TIME_LIMIT = "WT", _("Wall time limit")
        CPU_TIME_LIMIT = "TL", _("Time limit")
        MEMORY_LIMIT = "ML", _("Memory limit")

    class ExitStatus(CompositeField):
        class Type(models.TextChoices):
            EXITED = "E", _("Exited")
            SIGNALED = "S", _("Signaled")

        def __init__(self, type=None, code=None, *args, **kwargs):
            super().__init__(*args, **kwargs)
            self.type = type
            self.code = code

        type = models.CharField(max_length=1, choices=Type.choices)
        code = models.SmallIntegerField()

        @staticmethod
        def FromExec(stat: str):
            type, code = stat.split()
            t = None
            if type == "exited":
                t = AbstractRunResult.ExitStatus.Type.EXITED
            elif type == "signaled":
                t = AbstractRunResult.ExitStatus.Type.SIGNALED
            return AbstractRunResult.ExitStatus(type=t, code=int(code))

        class Proxy(CompositeField.Proxy):
            def isOk(self):
                return self.type == AbstractRunResult.ExitStatus.Type.EXITED and \
                       self.code == 0

    cpuUsage = models.DurationField()
    wallTime = models.DurationField()
    maxMemoryBytes = models.PositiveIntegerField()
    verdict = models.CharField(max_length=2, choices=RunResult.choices)
    exitStatus = ExitStatus()

    class Meta:
        abstract = True


class CompilationResult(AbstractRunResult):
    errorLog = models.CharField(max_length=EXEC_ID_MAXLENGTH)
    binaryId = models.CharField(max_length=EXEC_ID_MAXLENGTH)

    @staticmethod
    def FromExec(status):
        stats = {k: v for (k, v) in map(lambda x: x.split(": "), status['stats'].strip().split('\n'))}
        r = CompilationResult(
            cpuUsage=timezone.timedelta(microseconds=int(stats["time.cpu.total"])),
            wallTime=timezone.timedelta(microseconds=int(stats["time.wall"])),
            maxMemoryBytes=int(stats["memory.max"]),
            verdict=AbstractRunResult.RunResult(stats["verdict"]),
            exitStatus=AbstractRunResult.ExitStatus.FromExec(stats["status"]),
            errorLog=status["error-log-id"],
            binaryId=status.get("binary-id", ""),
        )
        r.save()
        return r


class Submission(models.Model):
    class CompilationStatus(models.TextChoices):
        ENQUEUED = "EN", _("Enqueued")
        RUNNING = "RU", _("Running")
        FINISHED = "FI", _("Finished")
        UNKNOWN = "UN", _("Unknown")

        @staticmethod
        def FromExecString(s: str):
            if s == "enqueued":
                return Submission.CompilationStatus.ENQUEUED
            if s == "processing":
                return Submission.CompilationStatus.RUNNING
            if s == "finished":
                return Submission.CompilationStatus.FINISHED
            return Submission.CompilationStatus.UNKNOWN

    execId = models.CharField(max_length=EXEC_ID_MAXLENGTH)
    status = models.CharField(
        max_length=2,
        choices=CompilationStatus.choices,
        default=CompilationStatus.ENQUEUED,
    )
    sourceId = models.CharField(max_length=EXEC_ID_MAXLENGTH)
    nextCheck = models.DateTimeField(default=timezone.now, null=True)
    compilationResult = models.ForeignKey(to=CompilationResult, on_delete=models.CASCADE, null=True, blank=True)
    timestamp = models.DateTimeField(default=timezone.now)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)

    def tryUpdate(self, force=False):
        if (self.nextCheck is None or self.nextCheck > timezone.now()) and not force:
            return
        status = getSubmissionStatus(self.execId)
        print(f"{status=}")
        curStatus = Submission.CompilationStatus.FromExecString(status['status'])
        if curStatus == self.status:
            self.nextCheck = timezone.now() + timezone.timedelta(milliseconds=500)
            self.save()
            return
        self.status = curStatus

        if self.status == Submission.CompilationStatus.RUNNING:
            self.save()
            return

        self.nextCheck = None
        if self.status == Submission.CompilationStatus.UNKNOWN:
            self.save()
            return

        try:
            self.compilationResult = CompilationResult.FromExec(status)
        except Exception as e:
            print(f"Exception caught while trying to fetch result from exec: {e}")
            self.status = Submission.CompilationStatus.UNKNOWN

        self.save()

    def overallStatus(self) -> 'OverallCompilationResult':
        if self.status != Submission.CompilationStatus.FINISHED:
            return OverallCompilationResult.FromCompilationStatus(self.status)
        if self.compilationResult.verdict != AbstractRunResult.RunResult.OK:
            return OverallCompilationResult.FromRunResult(self.compilationResult.verdict)
        if not self.compilationResult.exitStatus.isOk():
            return OverallCompilationResult.COMPILATION_ERROR
        return OverallCompilationResult.OK


class OverallCompilationResult(models.TextChoices):
    OK = AbstractRunResult.RunResult.OK
    WALL_TIME_LIMIT = AbstractRunResult.RunResult.WALL_TIME_LIMIT
    CPU_TIME_LIMIT = AbstractRunResult.RunResult.CPU_TIME_LIMIT
    MEMORY_LIMIT = AbstractRunResult.RunResult.MEMORY_LIMIT

    @staticmethod
    def FromRunResult(rr: AbstractRunResult.RunResult) -> 'OverallCompilationResult':
        if rr == AbstractRunResult.RunResult.OK:
            return OverallCompilationResult.OK
        if rr == AbstractRunResult.RunResult.WALL_TIME_LIMIT:
            return OverallCompilationResult.WALL_TIME_LIMIT
        if rr == AbstractRunResult.RunResult.CPU_TIME_LIMIT:
            return OverallCompilationResult.CPU_TIME_LIMIT
        if rr == AbstractRunResult.RunResult.WALL_TIME_LIMIT:
            return OverallCompilationResult.WALL_TIME_LIMIT

    ENQUEUED = Submission.CompilationStatus.ENQUEUED
    RUNNING = Submission.CompilationStatus.RUNNING
    UNKNOWN = Submission.CompilationStatus.UNKNOWN

    @staticmethod
    def FromCompilationStatus(cs: Submission.CompilationStatus) -> 'OverallCompilationResult':
        if cs == Submission.CompilationStatus.ENQUEUED:
            return OverallCompilationResult.ENQUEUED
        if cs == Submission.CompilationStatus.RUNNING:
            return OverallCompilationResult.RUNNING
        if cs == Submission.CompilationStatus.UNKNOWN:
            return OverallCompilationResult.UNKNOWN

    COMPILATION_ERROR = "CE", _("Compilation error")
