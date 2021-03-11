from django.urls import path

from . import views

urlpatterns = [
  # home
  path('', views.home, name='home'),
  
  # auth
  path('signin', views.sign_in, name='signin'),
  path('signout', views.sign_out, name='signout'),
  path('auth_callback', views.auth_callback, name='auth_callback'),

  # calendar views
  path('calendar', views.calendar, name='calendar'),
  path('calendar/new', views.newevent, name='newevent'),
  path('calendar/edit/<id>', views.editevent, name='editevent'),
  path('calendar/delete/<id>', views.delevent, name='delevent'),
  path('calendar/viewmap', views.viewmap, name='viewmap'),
]
