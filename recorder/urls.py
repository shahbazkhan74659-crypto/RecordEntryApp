from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('batch/', views.batch, name='batch'),
    path('batch/<slug:slug>/', views.batch_detail, name='batch_detail'),
    path('batch/<slug:slug>/edit/', views.batch_edit, name='batch_edit'),
    path('batch/<slug:slug>/delete/', views.delete_batch, name='delete_batch'),
    path('entries/delete/', views.delete_entries, name='delete_entries'),
    path('entries/<int:pk>/edit/', views.edit_entry, name='edit_entry'),
    path('entries/group/', views.create_batch, name='create_batch'),
]
