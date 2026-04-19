from django.urls import path
from django.contrib.auth import views as auth_views
from .views import cadastro_aluno_view

urlpatterns = [
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
    path('cadastro/aluno/', cadastro_aluno_view, name='cadastro_aluno'),
   
    path('reset_password/', auth_views.PasswordResetView.as_view(
        template_name='registration/password_reset_form.html',
        success_url='/?status=email_sent'
    ), name='password_reset'),

    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='registration/password_reset_confirm.html',
        success_url='/?status=reset_complete'
    ), name='password_reset_confirm'),
]