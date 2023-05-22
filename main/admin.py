from django.contrib import admin

from .models import Submission, CompilationResult

# Register your models here.
admin.site.register(Submission)
admin.site.register(CompilationResult)