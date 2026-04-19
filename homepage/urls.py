from django.urls import path
from .views import (
    painel_principal, 
    criar_turma, 
    entrar_turma, 
    painel_turma,
    criar_atividade,
    ver_alunos,
    ranking_turma,
    entregar_atividade,
    alterar_pontos,
    editar_atividade,
    deletar_atividade,
    deletar_turma,
    conectar_planilha_google,
    minhas_conquistas 
)

urlpatterns = [
    # URLs do Painel e Turma
    path('', painel_principal, name='painel'),
    path('turma/criar/', criar_turma, name='criar_turma'),
    path('turma/entrar/', entrar_turma, name='entrar_turma'),
    path('turma/<int:turma_id>/', painel_turma, name='painel_turma'),
    path('turma/<int:turma_id>/criar-atividade/', criar_atividade, name='criar_atividade'),
    path('turma/<int:turma_id>/alunos/', ver_alunos, name='ver_alunos'),
    path('turma/<int:turma_id>/ranking/', ranking_turma, name='ranking_turma'),
    path('turma/<int:turma_id>/deletar/', deletar_turma, name='deletar_turma'),
    path('atividade/<int:atividade_id>/entregar/', entregar_atividade, name='entregar_atividade'),
    path('atividade/<int:atividade_id>/editar/', editar_atividade, name='editar_atividade'),
    path('atividade/<int:atividade_id>/deletar/', deletar_atividade, name='deletar_atividade'),
    path('inscricao/<int:inscricao_id>/alterar-pontos/', alterar_pontos, name='alterar_pontos'),
    path('turma/<int:turma_id>/conectar-google/', conectar_planilha_google, name='conectar_planilha'),
    path('minhas-conquistas/', minhas_conquistas, name='minhas_conquistas'),
]