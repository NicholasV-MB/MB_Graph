from django.urls import path

from . import views

urlpatterns = [
  # /
  path('', views.home, name='home'),
  # TEMPORARY
  path('signin', views.sign_in, name='signin'),
  path('signout', views.sign_out, name='signout'),
  path('calendar', views.calendar, name='calendar'),
  path('auth_callback', views.auth_callback, name='auth_callback'),
  path('calendar/new', views.newevent, name='newevent'),
  path('calendar/edit/<id>', views.editevent, name='editevent'),
  path('calendar/delete/<id>', views.delevent, name='delevent'),
  path('calendar/viewmap', views.viewmap, name='viewmap'),
]
