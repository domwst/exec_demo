from django.db.models.base import ModelBase
from abc import ABCMeta


class ABCModelMeta(ABCMeta, ModelBase):
    pass
