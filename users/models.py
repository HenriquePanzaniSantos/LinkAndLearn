from django.db import models
from django.contrib.auth.models import AbstractUser
from .managers import CustomUserManager

class Usuario (AbstractUser):
    username = None
    email = models.EmailField('endereço de email', unique = True)
    
    TIPO_USUARIO_CHOICES = (
        ("aluno", "Aluno"),
        ("professor", "Professor"),
    )
    tipo_usuario = models.CharField(max_length = 20, choices = TIPO_USUARIO_CHOICES )
    
    ra = models. CharField(max_length = 20, unique = True, null = True, blank = True)
    
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []
    
    objects = CustomUserManager()
    
    def __str__(self):
        return self.email