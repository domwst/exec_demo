from django.urls import path

from .views import (
    SubmissionsView,
    SubmissionView,
    LoginView,
    Index,
    LogoutView,
    SignupView,
    RunView,
    RunsView,
    CreateRunView,
)

url_patterns = [
    path('', Index.as_view(), name='index'),
    path('login', LoginView.as_view(), name='login'),
    path('signup', SignupView.as_view(), name='signup'),
    path('logout', LogoutView.as_view(), name='logout'),
    path('submissions', SubmissionsView.as_view(), name='submissions'),
    path('submission/<int:id>', SubmissionView.as_view(), name='submission'),
    path('run/<int:id>', RunView.as_view(), name='run'),
    path('runs', RunsView.as_view(), name='runs'),
    path('createRun/<int:id>', CreateRunView.as_view(), name='create-run')
]
