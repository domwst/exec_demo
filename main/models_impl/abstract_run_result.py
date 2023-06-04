from __future__ import annotations

from typing import Any, Dict

from django.db import models
from django.utils.translation import gettext_lazy as _
from composite_field import CompositeField
from main.tools import exec_api as execApi


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
        def FromExec(status: execApi.ExitStatus):
            tp, code = status.type, status.code
            t = None
            if tp == execApi.ExitStatus.Type.EXITED:
                t = AbstractRunResult.ExitStatus.Type.EXITED
            elif tp == execApi.ExitStatus.Type.SIGNALED:
                t = AbstractRunResult.ExitStatus.Type.SIGNALED
            return AbstractRunResult.ExitStatus(type=t, code=code)

        class Proxy(CompositeField.Proxy):
            def isOk(self):
                return self.type == AbstractRunResult.ExitStatus.Type.EXITED and \
                       self.code == 0

    cpuTotalUsage = models.DurationField()
    cpuSystemUsage = models.DurationField()
    cpuUserUsage = models.DurationField()
    wallTime = models.DurationField()
    maxMemoryBytes = models.PositiveIntegerField()
    verdict = models.CharField(max_length=2, choices=RunResult.choices)
    exitStatus = ExitStatus()

    @staticmethod
    def FromExec(stats: execApi.Statistics) -> Dict[str, Any]:
        return dict(
            cpuTotalUsage=stats.cpuTotalTime,
            cpuSystemUsage=stats.cpuSystemTime,
            cpuUserUsage=stats.cpuUserTime,
            wallTime=stats.wallTime,
            maxMemoryBytes=stats.maxMemory,
            verdict=stats.verdict,
            exitStatus=AbstractRunResult.ExitStatus.FromExec(stats.exitStatus),
        )

    class Meta:
        abstract = True


class ExecStatus(models.TextChoices):
    ENQUEUED = "EN", _("Enqueued")
    RUNNING = "RU", _("Running")
    FINISHED = "FI", _("Finished")

    @staticmethod
    def FromExec(s: execApi.ExecStatus) -> ExecStatus:
        if s == execApi.ExecStatus.ENQUEUED:
            return ExecStatus.ENQUEUED
        if s == execApi.ExecStatus.PROCESSING:
            return ExecStatus.RUNNING
        if s == execApi.ExecStatus.FINISHED:
            return ExecStatus.FINISHED


class OverallRunStatus(models.TextChoices):
    OK = AbstractRunResult.RunResult.OK
    WALL_TIME_LIMIT = AbstractRunResult.RunResult.WALL_TIME_LIMIT
    CPU_TIME_LIMIT = AbstractRunResult.RunResult.CPU_TIME_LIMIT
    MEMORY_LIMIT = AbstractRunResult.RunResult.MEMORY_LIMIT

    @staticmethod
    def FromRunResult(rr: AbstractRunResult.RunResult) -> OverallRunStatus:
        if rr == AbstractRunResult.RunResult.OK:
            return OverallRunStatus.OK
        if rr == AbstractRunResult.RunResult.WALL_TIME_LIMIT:
            return OverallRunStatus.WALL_TIME_LIMIT
        if rr == AbstractRunResult.RunResult.CPU_TIME_LIMIT:
            return OverallRunStatus.CPU_TIME_LIMIT
        if rr == AbstractRunResult.RunResult.MEMORY_LIMIT:
            return OverallRunStatus.MEMORY_LIMIT

    ENQUEUED = ExecStatus.ENQUEUED
    RUNNING = ExecStatus.RUNNING

    @staticmethod
    def FromExecStatus(cs: ExecStatus) -> 'OverallRunStatus':
        if cs == ExecStatus.ENQUEUED:
            return OverallRunStatus.ENQUEUED
        if cs == ExecStatus.RUNNING:
            return OverallRunStatus.RUNNING

    RUNTIME_ERROR = "RT", _("Run-time error")