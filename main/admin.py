from django.contrib import admin

from .models import Submission, CompilationResult, Run, RunResult

# Register your models here.
admin.site.register(Submission)
admin.site.register(CompilationResult)
admin.site.register(Run)
admin.site.register(RunResult)