from django import forms
from .models import Atividade, Turma

class TurmaForm(forms.ModelForm):
    class Meta:
        model = Turma
        fields = ['nome', 'descricao', 'chave_publica_pem']
        widgets = {
            'chave_publica_pem': forms.Textarea(attrs={'rows': 5, 'placeholder': 'Cole aqui a chave pública RSA...'}),
        }

class EntrarTurmaForm(forms.Form):
    codigo_acesso = forms.CharField(label="Código de Acesso da Turma", max_length=10)

class AtividadeForm(forms.ModelForm):
    class Meta:
        model = Atividade
        fields = ['titulo', 'descricao', 'vale_xp', 'pontos', 'data_entrega']

        labels = {
            'titulo': 'Título do Aviso ou Atividade',
            'descricao': 'Instruções / Descrição',
            'pontos': 'Pontos de XP',
            'data_entrega': 'Data de Entrega',
        }
        
        widgets = {
            'descricao': forms.Textarea(attrs={'rows': 4}),
            'data_entrega': forms.DateInput(attrs={'type': 'date'}),
        }