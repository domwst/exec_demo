import requests
from django.conf import settings


def submit(file: bytes):
    resp = requests.post(
        settings.EXEC_API_URL + f"/submit?token={settings.EXEC_API_TOKEN}",
        files={'file': file},
    )
    resp.raise_for_status()
    return resp.json()


def getSubmissionStatus(id: str):
    resp = requests.get(
        settings.EXEC_API_URL + f'/compileStatus?token={settings.EXEC_API_TOKEN}&id={id}',
    )
    resp.raise_for_status()
    return resp.json()


def getArtifact(id: str) -> bytes:
    resp = requests.get(
        settings.EXEC_API_URL + f"/downloadArtifact?token={settings.EXEC_API_TOKEN}&id={id}",
    )
    resp.raise_for_status()
    return resp.text.encode()

