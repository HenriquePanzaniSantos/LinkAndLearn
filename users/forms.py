# users/forms.py
from django.contrib.auth.forms import UserCreationForm
from .models import Usuario

class AlunoCadastroForm(UserCreationForm):
    class Meta:
        model = Usuario
        # 1.lista exata dos campos
        #    O Django adiciona os campos de senha ('password' e 'password2') automaticamente.
        fields = ('first_name', 'last_name', 'email')

        # 2. (Opcional, mas recomendado) Customizamos os rótulos que aparecem na tela.
        labels = {
            'first_name': 'Nome',
            'last_name': 'Sobrenome',
            'email': 'Email Institucional',
        }