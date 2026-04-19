from django.contrib import admin
from .models import Turma, Conquista, ConquistaAluno

# Registra a Turma (do jeito simples que já estava)
admin.site.register(Turma)

# Registra a tabela para CRIAR medalhas
@admin.register(Conquista)
class ConquistaAdmin(admin.ModelAdmin):
    list_display = ('titulo', 'chave', 'imagem_arquivo')

# Registra a tabela para VER QUEM GANHOU
@admin.register(ConquistaAluno)
class ConquistaAlunoAdmin(admin.ModelAdmin):
    list_display = ('aluno', 'conquista', 'data_conquista')