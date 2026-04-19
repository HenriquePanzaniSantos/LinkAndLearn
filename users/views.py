# users/views.py
from django.shortcuts import get_object_or_404, render, redirect
from django.contrib import messages
from homepage.models import Atividade, Inscricao
from .forms import AlunoCadastroForm
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied

def cadastro_aluno_view(request):
    if request.method == 'POST':
        form = AlunoCadastroForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.tipo_usuario = 'aluno' # Define o tipo de usuário
            user.save()
            messages.success(request, 'Conta criada com sucesso! Faça o login para continuar.')
            return redirect('login')
    else:
        form = AlunoCadastroForm()
    
    return render(request, 'users/cadastro_aluno.html', {'form': form})

@login_required
def entregar_atividade(request, atividade_id):
    atividade = get_object_or_404(Atividade, pk=atividade_id)
    turma = atividade.turma
    user = request.user

    # Tenta encontrar a inscrição do aluno nesta turma
    try:
        inscricao = Inscricao.objects.get(aluno=user, turma=turma)
    except Inscricao.DoesNotExist:
        raise PermissionDenied("Você não está inscrito nesta turma.")

    # Verifica se a atividade já foi concluída
    if inscricao.atividades_concluidas.filter(pk=atividade.pk).exists():
        messages.warning(request, 'Você já concluiu esta atividade.')
        return redirect('painel_turma', turma_id=turma.id)

    # Lógica de processamento
    if request.method == 'POST':
        # Cenário 1: Atividade com Código
        if atividade.codigo_conclusao:
            codigo_enviado = request.POST.get('codigo', '').strip().upper()
            if codigo_enviado == atividade.codigo_conclusao.strip().upper():
                # Código CORRETO
                inscricao.pontos += atividade.pontos
                inscricao.atividades_concluidas.add(atividade)
                inscricao.save()
                messages.success(request, f'Código correto! Você ganhou {atividade.pontos} pontos.')
            else:
                # Código INCORRETO
                messages.error(request, 'Código de conclusão incorreto. Tente novamente.')
        
        # Cenário 2: Atividade sem Código (Sistema de Honra)
        else:
            inscricao.pontos += atividade.pontos
            inscricao.atividades_concluidas.add(atividade)
            inscricao.save()
            messages.success(request, f'Atividade concluída! Você ganhou {atividade.pontos} pontos.')
            
    return redirect('painel_turma', turma_id=turma.id)