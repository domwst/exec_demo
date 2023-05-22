from django.urls import path

from .views import SubmissionsView, SubmissionView, DownloadBinary, Login, Index, Logout

urls = [
    path('', Index.as_view(), name='index'),
    path('login', Login.as_view(), name='login'),
    path('logout', Logout.as_view(), name='logout'),
    path('submissions', SubmissionsView.as_view(), name='submissions'),
    path('submission/<int:id>', SubmissionView.as_view(), name='submission'),
    path('download/<str:id>', DownloadBinary.as_view(), name='download-binary'),
]
