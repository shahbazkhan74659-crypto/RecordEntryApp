from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('batch/', views.batch, name='batch'),
    path('batch/<slug:slug>/', views.batch_detail, name='batch_detail'),
    path('batch/<slug:slug>/edit/', views.batch_edit, name='batch_edit'),
    path('batch/<slug:slug>/delete/', views.delete_batch, name='delete_batch'),
    path('entries/new/', views.create_entry, name='create_entry'),
    path('entries/delete/', views.delete_entries, name='delete_entries'),
    path('entries/<int:pk>/edit/', views.edit_entry, name='edit_entry'),
    path('entries/group/', views.create_batch, name='create_batch'),
    path('entries/download-pdf/', views.download_entries_pdf, name='download_entries_pdf'),
    path('account/change-username/', views.change_username, name='change_username'),
    path('account/change-password/', views.change_password, name='change_password'),
    path('account/change-email/request-otp/', views.change_email_request_otp, name='change_email_request_otp'),
    path('account/change-email/verify/', views.change_email_verify, name='change_email_verify'),
    path('account/change-email/revert/', views.change_email_revert, name='change_email_revert'),
    path('forgot-password/check-username/', views.check_username, name='check_username'),
    path('forgot-password/request-otp/', views.forgot_password_request_otp, name='forgot_password_request_otp'),
    path('forgot-password/verify-otp/', views.forgot_password_verify_otp, name='forgot_password_verify_otp'),
    path('forgot-password/reset/', views.forgot_password_reset, name='forgot_password_reset'),
]
