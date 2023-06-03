from __future__ import annotations

import datetime
import sys

from enum import Enum
import httpx
from dataclasses import dataclass
from typing import Optional

from django.conf import settings

# time.wall: 4010041
# time.cpu.total: 4005683
# time.cpu.user: 3997696
# time.cpu.system: 7987
# memory.max: 286720
# status: signaled 9
# verdict: TL


@dataclass
class ExitStatus:
    class Type(Enum):
        SIGNALED = "Signaled"
        EXITED = "Exited"

    code: int
    type: ExitStatus.Type

    @staticmethod
    def FromExec(status: str) -> ExitStatus:
        tp, code = status.split()
        if tp == "signaled":
            tp = ExitStatus.Type.SIGNALED
        elif tp == "exited":
            tp = ExitStatus.Type.EXITED
        else:
            print(f"Unknown exit type: {tp}", file=sys.stderr)
        return ExitStatus(code=int(code), type=tp)


@dataclass
class Statistics:
    wallTime: datetime.timedelta
    cpuTotalTime: datetime.timedelta
    cpuUserTime: datetime.timedelta
    cpuSystemTime: datetime.timedelta
    maxMemory: int
    exitStatus: ExitStatus
    verdict: str

    @staticmethod
    def FromExec(statistics: str):
        stats = {k: v for k, v in map(lambda x: x.split(": "), statistics.strip().split('\n'))}
        return Statistics(
            wallTime=datetime.timedelta(microseconds=int(stats["time.wall"])),
            cpuTotalTime=datetime.timedelta(microseconds=int(stats["time.cpu.total"])),
            cpuUserTime=datetime.timedelta(microseconds=int(stats["time.cpu.user"])),
            cpuSystemTime=datetime.timedelta(microseconds=int(stats["time.cpu.system"])),
            maxMemory=int(stats["memory.max"]),
            exitStatus=ExitStatus.FromExec(stats["status"]),
            verdict=stats["verdict"],
        )


@dataclass
class CompilationOutcome:
    binaryId: Optional[str]
    errorLogId: str
    statistics: Statistics

    @staticmethod
    def FromExec(json) -> CompilationOutcome:
        return CompilationOutcome(
            binaryId=json.get("binary-id"),
            errorLogId=json["error-log-id"],
            statistics=Statistics.FromExec(json["stats"])
        )


class ExecStatus(Enum):
    ENQUEUED = "Enqueued"
    PROCESSING = "Processing"
    FINISHED = "Finished"

    @staticmethod
    def FromExec(status: str) -> ExecStatus:
        if status == "enqueued":
            return ExecStatus.ENQUEUED
        elif status == "processing":
            return ExecStatus.PROCESSING
        elif status == "finished":
            return ExecStatus.FINISHED
        else:
            print(f"Unknown exec status: {status}", file=sys.stderr)


@dataclass
class CompilationStatus:
    execStatus: ExecStatus
    outcome: Optional[CompilationOutcome]

    @staticmethod
    def FromExec(json) -> CompilationStatus:
        status = ExecStatus.FromExec(json["status"])
        outcome = None
        if status == ExecStatus.FINISHED:
            outcome = CompilationOutcome.FromExec(json)

        return CompilationStatus(
            execStatus=status,
            outcome=outcome,
        )


@dataclass
class RunOutcome:
    stdoutId: str
    stderrId: str
    statistics: Statistics

    @staticmethod
    def FromExec(json) -> RunOutcome:
        return RunOutcome(
            stdoutId=json["stdout-id"],
            stderrId=json["stderr-id"],
            statistics=Statistics.FromExec(json["stats"]),
        )


@dataclass
class RunStatus:
    execStatus: ExecStatus
    outcome: Optional[RunOutcome]

    @staticmethod
    def FromExec(json) -> RunStatus:
        status = ExecStatus.FromExec(json["status"])
        outcome = None
        if status == ExecStatus.FINISHED:
            outcome = RunOutcome.FromExec(json)
        return RunStatus(
            execStatus=status,
            outcome=outcome,
        )


class ExecApi:
    def __init__(self, url=settings.EXEC_API_URL, token=settings.EXEC_API_TOKEN):
        self.url = url
        self.token = token

    def submit(self, file: bytes):
        resp = httpx.post(
            f'{self.url}/submit',
            params={'token': self.token},
            files={'file': file},
        )
        resp.raise_for_status()
        return resp.json()

    def getSubmissionStatus(self, id: str) -> CompilationStatus:
        resp = httpx.get(
            f'{self.url}/compileStatus',
            params={
                'token': self.token,
                'id': id,
            },
        )
        resp.raise_for_status()
        return CompilationStatus.FromExec(resp.json())

    def getArtifact(self, id: str) -> bytes:
        resp = httpx.get(
            f'{self.url}/downloadArtifact',
            params={
                'token': self.token,
                'id': id,
            },
        )
        return resp.text.encode()

    def run(self, id: str) -> str:
        resp = httpx.post(
            f'{self.url}/run',
            params={
                'token': self.token,
                'id': id,
            }
        )
        resp.raise_for_status()
        return resp.json()["id"]

    def getRunStatus(self, id: str) -> RunStatus:
        resp = httpx.get(
            f"{self.url}/runStatus",
            params={
                'token': self.token,
                'id': id,
            }
        )
        resp.raise_for_status()
        return RunStatus.FromExec(resp.json())


execApi = ExecApi()
