# homepage/views.py

from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Sum
from django.core.exceptions import PermissionDenied
from django.contrib import messages
from django.conf import settings
import gspread
import threading
import re
import os
import json
from datetime import datetime
import base64
from Crypto.PublicKey import RSA

from .models import Atividade, Conclusao, Conquista, ConquistaAluno, Inscricao, Turma 
from .forms import AtividadeForm, TurmaForm, EntrarTurmaForm

GOOGLE_CREDENTIALS_FILE = os.path.join(settings.BASE_DIR, 'google-credentials.json')

# =============================================================================
#  FUNÇÕES AUXILIARES (ROBÔS E LÓGICA REUTILIZÁVEL)
# =============================================================================

def extrair_ra_do_email(email):
    """Extrai apenas os números do prefixo do e-mail (ex: aluno123@... -> 123)."""
    prefixo = email.split('@')[0]
    return re.sub(r'\D', '', prefixo) or "000000"

import base64
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5

from Crypto.PublicKey import RSA
from Crypto.Signature import pkcs1_15
from Crypto.Hash import SHA256
import base64

# homepage/views.py

def validar_voucher_rsa(voucher_base64, public_key_pem):
    try:
        # CORREÇÃO DE PADDING: Garante que a string tenha tamanho múltiplo de 4
        missing_padding = len(voucher_base64) % 4
        if missing_padding:
            voucher_base64 += '=' * (4 - missing_padding)
            
        decoded_bundle = base64.b64decode(voucher_base64)
        key = RSA.importKey(public_key_pem)
        signature_size = key.size_in_bytes()
        
        dados_brutos = decoded_bundle[:-signature_size]
        assinatura = decoded_bundle[-signature_size:]
        
        h = SHA256.new(dados_brutos)
        pkcs1_15.new(key).verify(h, assinatura)
        
        texto_claro = dados_brutos.decode('utf-8')
        dados = {}
        for item in texto_claro.split('|'):
            if ':' in item:
                # Usamos .strip() e .upper() para evitar erros de digitação do professor
                k, v = item.split(':', 1)
                dados[k.strip().upper()] = v.strip()
        
        return dados 
    except Exception as e:
        print(f"❌ Erro na validação: {e}") # Aqui vai aparecer o erro real no console
        return None


def entregar_atividade(request, atividade_id):
    # 1. Identificação Inicial
    atividade = get_object_or_404(Atividade, pk=atividade_id)
    turma = atividade.turma
    user = request.user
    inscricao = get_object_or_404(Inscricao, aluno=user, turma=turma)

    print(f"\n--- 🔍 INÍCIO DA VALIDAÇÃO (Atividade ID: {atividade_id}) ---")
    print(f"👤 Aluno: {user.email} | RA extraído: {extrair_ra_do_email(user.email)}")

    # Verifica duplicidade
    ja_concluiu = Conclusao.objects.filter(inscricao=inscricao, atividade=atividade).exists()
    if ja_concluiu:
        print("⛔ BLOQUEIO: Aluno já tinha concluído esta atividade.")
        messages.warning(request, 'Você já concluiu esta atividade.')
        return redirect('painel_turma', turma_id=turma.id)

    if request.method == 'POST':
        voucher_bruto = request.POST.get('codigo', '').strip()
        print(f"📦 Voucher recebido (truncado): {voucher_bruto[:20]}...")

        if not turma.chave_publica_pem:
            print("❌ ERRO: Turma não tem chave pública cadastrada no banco.")
            messages.error(request, 'Erro: Turma sem Chave Pública.')
            return redirect('painel_turma', turma_id=turma.id)

        # 2. Tentativa de decodificação RSA
        dados_voucher = validar_voucher_rsa(voucher_bruto, turma.chave_publica_pem)
        
        if not dados_voucher:
            print("❌ ERRO: validar_voucher_rsa retornou None (Assinatura inválida ou Formato errado).")
            messages.error(request, 'Voucher inválido ou corrompido.')
            return redirect('painel_turma', turma_id=turma.id)

        print(f"✅ Voucher Decodificado com Sucesso: {dados_voucher}")

        # 3. Confronto de IDs (Onde está o seu erro atual)
        # Vamos buscar por ATIV, ID ou ATIVIDADE para não ter erro
        id_no_voucher = str(dados_voucher.get('ATIV') or dados_voucher.get('ID') or dados_voucher.get('ATIVIDADE', 'NÃO ENCONTRADO'))
        id_esperado = str(atividade.id)

        print(f"⚖️ Comparando IDs: No Voucher [{id_no_voucher}] vs Na Página [{id_esperado}]")

        if id_no_voucher != id_esperado:
            print(f"🚫 BLOQUEIO: IDs não batem! Voucher é da ativ {id_no_voucher}")
            messages.error(request, f'Este voucher é para a atividade #{id_no_voucher}, não para esta.')
            return redirect('painel_turma', turma_id=turma.id)

        # 4. Confronto de RA
        ra_logado = extrair_ra_do_email(user.email)
        ra_voucher = str(dados_voucher.get('RA', '')).strip() # .strip() remove espaços acidentais
        
        print(f"Comparando RAs: No Voucher [{ra_voucher}] vs Logado [{ra_logado}]")

        if ra_voucher != ra_logado:
            print(f"🚫 BLOQUEIO: RA divergente. Voucher pertence a {ra_voucher}")
            messages.error(request, f'Este voucher não pertence ao seu RA.')
            return redirect('painel_turma', turma_id=turma.id)

        # 5. Tratamento Flexível da Nota (Ponto ou Vírgula)
        nota_raw = str(dados_voucher.get('NOTA', '0')).strip()
        
        # O "Pulo do Gato": Troca vírgula por ponto para o Python conseguir converter
        nota_limpa = nota_raw.replace(',', '.')
        
        try:
            nota_do_voucher = float(nota_limpa)
            print(f"📝 Nota processada: {nota_do_voucher}")
        except ValueError:
            print(f"⚠️ Erro ao converter nota: [{nota_raw}]. Definindo como 0.")
            nota_do_voucher = 0.0

        # 5. Finalização
        print("🚀 SUCESSO: Todas as travas passadas. Gravando no banco...")
        
        # ... (seu código de salvar Conclusao e Planilha continua aqui)
        # Lembre-se de usar a nota que veio do voucher!
        nota_voucher = float(dados_voucher.get('NOTA', 0))
        
        Conclusao.objects.create(
            inscricao=inscricao,
            atividade=atividade,
            pontos_ganhos=atividade.pontos, # ou sua lógica de bônus
            voucher_bruto=voucher_bruto,
            ra_validado=ra_voucher,
            nota_atribuida=nota_voucher
        )
        
        inscricao.pontos += atividade.pontos
        inscricao.save()
        
        print(f"💾 Salvo! +{atividade.pontos} XP para o aluno.")
        messages.success(request, 'Atividade concluída com sucesso!')

    print("--- 🏁 FIM DO PROCESSO ---\n")
    return redirect('painel_turma', turma_id=turma.id)

def calcular_gamificacao(aluno):
    """
    Calcula o nível, XP, título e porcentagem do aluno.
    Retorna um dicionário pronto para usar nos templates.
    """
    if aluno.tipo_usuario != 'aluno':
        return None

    # Soma todos os pontos de todas as turmas
    total_xp = Inscricao.objects.filter(aluno=aluno).aggregate(Sum('pontos'))['pontos__sum'] or 0
    
    xp_por_nivel = 1000
    nivel_atual = (total_xp // xp_por_nivel) + 1
    xp_no_nivel_atual = total_xp % xp_por_nivel
    
    porcentagem_prox_nivel = (xp_no_nivel_atual / xp_por_nivel) * 100
    
    # Definição de Títulos
    titulo = "Bixo"
    if nivel_atual >= 5: titulo = "Calouro"
    if nivel_atual >= 10: titulo = "Veterano"
    if nivel_atual >= 20: titulo = "Formando"

    return {
        'nivel': nivel_atual,
        'titulo': titulo,
        'xp_atual': xp_no_nivel_atual,
        'xp_meta': xp_por_nivel,
        'porcentagem': int(porcentagem_prox_nivel),
        'total_xp_geral': total_xp,
    }

def logar_entrega_na_planilha(turma_link, atividade_titulo, aluno_nome, aluno_email, pontos, nota):
    """Adicionamos o parâmetro 'nota' no final"""
    try:
        gc = gspread.service_account(filename=GOOGLE_CREDENTIALS_FILE)
        sh = gc.open_by_url(turma_link)
        
        try:
            worksheet = sh.worksheet(atividade_titulo)
        except gspread.WorksheetNotFound:
            worksheet = sh.add_worksheet(title=atividade_titulo, rows=100, cols=10)
            # Atualizamos o cabeçalho para incluir a Nota
            worksheet.append_row(["Data/Hora", "Aluno", "Email", "Pontos XP", "Nota Voucher"])
            
        data_hora = datetime.now().strftime('%d/%m/%Y %H:%M')
        # Adicionamos a nota na linha que será escrita
        worksheet.append_row([data_hora, aluno_nome, aluno_email, pontos, nota])
        
    except Exception as e:
        print(f"!!! ERRO ao escrever na planilha Google: {e}")

def configurar_aba_frequencia(turma_id):
    """Configura a aba 'Frequência' com layout padrão."""
    try:
        turma = Turma.objects.get(pk=turma_id)
        inscricoes = Inscricao.objects.filter(turma=turma).select_related('aluno').order_by('aluno__first_name')
        
        gc = gspread.service_account(filename=GOOGLE_CREDENTIALS_FILE)
        sh = gc.open_by_url(turma.google_sheet_link)
        
        try:
            worksheet = sh.worksheet("Frequência")
        except:
            worksheet = sh.get_worksheet(0)
            worksheet.update_title("Frequência")
        
        worksheet.clear()
        
        # 1. Cabeçalhos
        texto_instrucao = "⚠️ INSTRUÇÃO: Para presença digite 'Ok'. Para ausência digite 'Faltou'. O sistema soma os 'Faltou' automaticamente."
        worksheet.update_acell('A1', texto_instrucao)
        worksheet.merge_cells('A1:R1')
        worksheet.format('A1', {
            'textFormat': {'bold': True, 'foregroundColor': {'red': 0.8, 'green': 0, 'blue': 0}},
            'backgroundColor': {'red': 1, 'green': 0.95, 'blue': 0.8},
            'horizontalAlignment': 'CENTER'
        })

        cabecalho = ["RA", "Nome do Aluno", "Total Faltas", "Aula 01", "Aula 02", "Aula 03", "Aula 04", "Aula 05", "Aula 06", "Aula 07", "Aula 08", "Aula 09", "Aula 10", "Aula 11", "Aula 12", "Aula 13", "Aula 14", "Aula 15"]
        worksheet.append_row(cabecalho)
        
        # 2. Dados
        dados_para_enviar = []
        linha_atual = 3 
        
        for insc in inscricoes:
            email_prefix = insc.aluno.email.split('@')[0]
            ra = re.sub(r'\D', '', email_prefix) or "N/A"
            nome = insc.aluno.get_full_name().upper()
            formula_faltas = f'=CONT.SE(D{linha_atual}:{linha_atual}; "Faltou")'
            dados_para_enviar.append([ra, nome, formula_faltas])
            linha_atual += 1
            
        if dados_para_enviar:
            worksheet.append_rows(dados_para_enviar, value_input_option='USER_ENTERED')
            
        # 3. Formatação Final
        worksheet.freeze(rows=2, cols=3)
        worksheet.format('A2:Z2', {'textFormat': {'bold': True}, 'backgroundColor': {'red': 0.9, 'green': 0.9, 'blue': 0.9}})

    except Exception as e:
        print(f"❌ Erro frequência: {e}")

def adicionar_aluno_frequencia(turma_id, aluno):
    """Adiciona aluno novo na frequência."""
    try:
        turma = Turma.objects.get(pk=turma_id)
        if not turma.google_sheet_link: return

        gc = gspread.service_account(filename=GOOGLE_CREDENTIALS_FILE)
        sh = gc.open_by_url(turma.google_sheet_link)
        
        try: worksheet = sh.worksheet("Frequência")
        except: worksheet = sh.get_worksheet(0)
            
        nova_linha = len(worksheet.col_values(1)) + 1
        
        email_prefix = aluno.email.split('@')[0]
        ra = re.sub(r'\D', '', email_prefix) or "N/A"
        nome = aluno.get_full_name().upper()
        formula_faltas = f'=CONT.SE(D{nova_linha}:{nova_linha}; "Faltou")'
        
        worksheet.append_row([ra, nome, formula_faltas], value_input_option='USER_ENTERED')
        
    except Exception as e:
        print(f"❌ Erro ao add aluno: {e}")


# =============================================================================
#  VIEWS PRINCIPAIS
# =============================================================================

@login_required
def painel_principal(request):
    context = {}
    usuario_logado = request.user

    # 1. Medalha de Primeiro Acesso
    if usuario_logado.is_authenticated:
        try:
            medalha = Conquista.objects.get(chave='primeiro_acesso')
            obj, created = ConquistaAluno.objects.get_or_create(aluno=usuario_logado, conquista=medalha)
            if created:
                messages.success(request, f"Parabéns! Você ganhou a medalha: {medalha.titulo}")
        except Conquista.DoesNotExist:
            pass

    # 2. Carregar Turmas
    if usuario_logado.tipo_usuario == 'professor':
        turmas = usuario_logado.turmas_lecionadas.all()
        context['titulo_secao'] = 'Minhas Turmas'
    else: 
        turmas_ids = Inscricao.objects.filter(aluno=usuario_logado).values_list('turma_id', flat=True)
        turmas = Turma.objects.filter(pk__in=turmas_ids)
        context['titulo_secao'] = 'Minhas turmas'
    
    context['turmas'] = turmas

    # 3. Gamificação (Usando a função auxiliar)
    if usuario_logado.tipo_usuario == 'aluno':
        dados_gami = calcular_gamificacao(usuario_logado)
        if dados_gami:
            # Adiciona as medalhas especificamente para o painel principal
            dados_gami['medalhas'] = ConquistaAluno.objects.filter(aluno=usuario_logado)
            context['gamificacao'] = dados_gami

    return render(request, 'homepage/painel.html', context)


@login_required
def painel_turma(request, turma_id):
    turma = get_object_or_404(Turma, pk=turma_id)
    user = request.user

    is_professor = (user == turma.professor)
    is_aluno_matriculado = False
    inscricao = None

    if user.tipo_usuario == 'aluno':
        try:
            inscricao = Inscricao.objects.get(aluno=user, turma=turma)
            is_aluno_matriculado = True
        except Inscricao.DoesNotExist:
            is_aluno_matriculado = False
    
    if not (is_professor or is_aluno_matriculado):
        raise PermissionDenied("Você não tem permissão para ver esta página.")
    
    atividades = turma.atividades.all().order_by('-data_criacao')

    concluidas_ids = set()
    if is_aluno_matriculado and inscricao:
       concluidas_ids = set(Conclusao.objects.filter(inscricao=inscricao).values_list('atividade_id', flat=True))

    gamificacao = None
    if user.tipo_usuario == 'aluno':
        gamificacao = calcular_gamificacao(user)

    context = {
        'turma': turma,
        'atividades': atividades,
        'concluidas_ids': concluidas_ids,
        'inscricao': inscricao,
        'gamificacao': gamificacao  # Enviando para o template
    }
    return render(request, 'turma/detalhe_turma.html', context)


# =============================================================================
#  VIEWS DE TURMA
# =============================================================================

@login_required
def criar_turma(request):
    if request.user.tipo_usuario != 'professor':
        raise PermissionDenied

    if request.method == 'POST':
        form = TurmaForm(request.POST, request.FILES)
        if form.is_valid():
            nova_turma = form.save(commit=False)
            nova_turma.professor = request.user 
            nova_turma.save()
            return redirect('painel') 
    else:
        form = TurmaForm()
    
    return render(request, 'turma/criar_turma.html', {'form': form})


@login_required
def entrar_turma(request):
    if request.user.tipo_usuario != 'aluno':
        raise PermissionDenied

    if request.method == 'POST':
        form = EntrarTurmaForm(request.POST)
        if form.is_valid():
            codigo = form.cleaned_data.get('codigo_acesso')
            try:
                turma = Turma.objects.get(codigo_acesso=codigo)
                obj, created = Inscricao.objects.get_or_create(aluno=request.user, turma=turma)
                
                if created and turma.google_sheet_link:
                    threading.Thread(
                        target=adicionar_aluno_frequencia,
                        args=(turma.id, request.user)
                    ).start()
                
                messages.success(request, f'Você entrou na turma "{turma.nome}" com sucesso!')
                return redirect('painel')
            except Turma.DoesNotExist:
                form.add_error('codigo_acesso', 'Código da Turma inválido.')
    else:
        form = EntrarTurmaForm()

    return render(request, 'turma/entrar_turma.html', {'form': form})


@login_required
def ver_alunos(request, turma_id):
    turma = get_object_or_404(Turma, pk=turma_id)

    if request.user != turma.professor:
        raise PermissionDenied("Você não tem permissão para ver esta página.")

    search_query = request.GET.get('q', '') 
    inscricoes_queryset = Inscricao.objects.filter(turma=turma).select_related('aluno')

    if search_query:
        inscricoes_queryset = inscricoes_queryset.filter(
            Q(aluno__first_name__icontains=search_query) |
            Q(aluno__last_name__icontains=search_query) |
            Q(aluno__email__icontains=search_query)
        ).distinct()
    
    inscricoes = inscricoes_queryset.order_by('aluno__first_name', 'aluno__last_name')
    
    for insc in inscricoes:
        try:
            email_prefix = insc.aluno.email.split('@')[0]
            derived_ra = re.sub(r'\D', '', email_prefix)
            insc.derived_ra = derived_ra if derived_ra else "N/A"
        except Exception:
            insc.derived_ra = "N/A" 
        
    context = {
        'turma': turma,
        'inscricoes': inscricoes,
        'search_query': search_query,
    }
    return render(request, 'turma/ver_alunos.html', context)


@login_required
def ranking_turma(request, turma_id):
    turma = get_object_or_404(Turma, pk=turma_id)
    user = request.user
    
    is_professor = (user == turma.professor)
    is_aluno_matriculado = Inscricao.objects.filter(aluno=user, turma=turma).exists()

    if not (is_professor or is_aluno_matriculado):
        raise PermissionDenied("Você não tem permissão para ver esta página.")

    inscricoes = Inscricao.objects.filter(turma=turma).select_related('aluno').order_by('-pontos', 'aluno__first_name')

    context = {
        'turma': turma,
        'inscricoes': inscricoes,
    }
    return render(request, 'turma/ranking_turma.html', context)


@login_required
def deletar_turma(request, turma_id):
    turma = get_object_or_404(Turma, pk=turma_id, professor=request.user)

    if request.method == 'POST':
        nome_turma = turma.nome
        turma.delete()
        messages.success(request, f'A turma "{nome_turma}" foi deletada permanentemente.')
        return redirect('painel')
    else:
        return redirect('painel_turma', turma_id=turma.id)


@login_required
def conectar_planilha_google(request, turma_id):
    turma = get_object_or_404(Turma, pk=turma_id, professor=request.user)

    email_robo = "Erro ao ler e-mail"
    try:
        with open(GOOGLE_CREDENTIALS_FILE, 'r') as f:
            creds = json.load(f)
            email_robo = creds.get('client_email', 'Não encontrado')
    except Exception:
        pass

    if request.method == 'POST':
        link_enviado = request.POST.get('link_planilha')
        
        try:
            gc = gspread.service_account(filename=GOOGLE_CREDENTIALS_FILE)
            sh = gc.open_by_url(link_enviado)
            
            turma.google_sheet_link = link_enviado
            turma.save()
            
            threading.Thread(
                target=configurar_aba_frequencia,
                args=(turma.id,)
            ).start()
            
            messages.success(request, f'Conectado! A aba "Frequência" está sendo gerada com os alunos atuais.')
            return redirect('painel_turma', turma_id=turma.id)
            
        except gspread.SpreadsheetNotFound:
            messages.error(request, 'Não encontramos a planilha. Verifique o link.')
        except gspread.exceptions.APIError:
             messages.error(request, 'Permissão Negada. Você lembrou de compartilhar a planilha com o e-mail do robô?')
        except Exception as e:
            messages.error(request, f'Erro ao conectar: {e}')

    context = {
        'turma': turma,
        'email_robo': email_robo
    }
    return render(request, 'turma/conectar_planilha.html', context)


# =============================================================================
#  VIEWS DE ATIVIDADES E ENTREGAS
# =============================================================================

@login_required
def criar_atividade(request, turma_id):
    turma = get_object_or_404(Turma, pk=turma_id)

    if request.user != turma.professor:
        raise PermissionDenied("Você não tem permissão para adicionar atividades a esta turma.")

    if request.method == 'POST':
        form = AtividadeForm(request.POST, request.FILES)
        if form.is_valid():
            nova_atividade = form.save(commit=False)
            nova_atividade.turma = turma
            
            if not nova_atividade.vale_xp:
                nova_atividade.pontos = 0
                nova_atividade.codigo_conclusao = None
            
            nova_atividade.save()
            messages.success(request, 'Atividade adicionada com sucesso!')
            return redirect('painel_turma', turma_id=turma.id)
    else:
        form = AtividadeForm()

    context = {
        'form': form,
        'turma': turma,
    }
    return render(request, 'atividade/criar_atividade.html', context)


@login_required
def editar_atividade(request, atividade_id):
    atividade = get_object_or_404(Atividade, pk=atividade_id)
    turma = atividade.turma

    if request.user != turma.professor:
        raise PermissionDenied("Você não tem permissão para editar esta atividade.")

    if request.method == 'POST':
        form = AtividadeForm(request.POST, request.FILES, instance=atividade)
        if form.is_valid():
            ativ = form.save(commit=False)
            if not ativ.vale_xp:
                ativ.pontos = 0
                ativ.codigo_conclusao = None
            ativ.save()
            messages.success(request, 'Atividade atualizada com sucesso!')
            return redirect('painel_turma', turma_id=turma.id)
    else:
        form = AtividadeForm(instance=atividade)

    context = {
        'form': form,
        'turma': turma,
        'is_editing': True
    }
    return render(request, 'atividade/criar_atividade.html', context)


@login_required
def deletar_atividade(request, atividade_id):
    atividade = get_object_or_404(Atividade, pk=atividade_id)
    turma = atividade.turma

    if request.user != turma.professor:
        raise PermissionDenied("Você não tem permissão para deletar esta atividade.")

    if request.method == 'POST':
        atividade.delete()
        messages.success(request, 'Atividade deletada com sucesso.')
    
    return redirect('painel_turma', turma_id=turma.id)

@login_required
def entregar_atividade(request, atividade_id):
    # 1. Identificação Inicial
    atividade = get_object_or_404(Atividade, pk=atividade_id)
    turma = atividade.turma
    user = request.user
    inscricao = get_object_or_404(Inscricao, aluno=user, turma=turma)

    # --- TRAVA 1: DUPLICIDADE (Só aceita uma única vez) ---
    if Conclusao.objects.filter(inscricao=inscricao, atividade=atividade).exists():
        messages.warning(request, 'Você já concluiu esta atividade anteriormente.')
        return redirect('painel_turma', turma_id=turma.id)

    if request.method == 'POST':
        voucher_bruto = request.POST.get('codigo', '').strip()
        
        if not turma.chave_publica_pem:
            messages.error(request, 'Erro: Turma sem Chave Pública configurada.')
            return redirect('painel_turma', turma_id=turma.id)

        # 2. Valida o conteúdo do Voucher (RSA)
        dados_voucher = validar_voucher_rsa(voucher_bruto, turma.chave_publica_pem)
        
        if not dados_voucher:
            messages.error(request, 'Voucher inválido, corrompido ou assinatura ilegal.')
            return redirect('painel_turma', turma_id=turma.id)

        # --- TRAVA 2: SEGURANÇA DE ID (Voucher da Atividade X na Atividade Y) ---
        # Buscamos por 'ATIV' no dicionário gerado pelo RSA
        id_no_voucher = str(dados_voucher.get('ATIV', '')).strip()
        id_esperado = str(atividade.id).strip()

        if id_no_voucher != id_esperado:
            messages.error(request, f'Erro de Atividade: Este voucher pertence a outra atividade.')
            return redirect('painel_turma', turma_id=turma.id)

        # --- TRAVA 3: SEGURANÇA DE RA (Dono do Voucher) ---
        ra_logado = extrair_ra_do_email(user.email)
        ra_voucher = str(dados_voucher.get('RA', '')).strip()

        if ra_voucher != ra_logado:
            messages.error(request, 'Este voucher não pertence ao seu perfil (RA divergente).')
            return redirect('painel_turma', turma_id=turma.id)

        # 4. Cálculo de Pontos e Nota
        conclusoes_anteriores = Conclusao.objects.filter(atividade=atividade).count()
        pontos_base = atividade.pontos
        
        # Lógica de Bônus (opcional, se quiser remover é só deixar pontos_totais = pontos_base)
        pontos_bonus = 0
        if conclusoes_anteriores == 0: pontos_bonus = int(pontos_base * 0.5)
        elif conclusoes_anteriores == 1: pontos_bonus = int(pontos_base * 0.25)
        
        pontos_totais = pontos_base + pontos_bonus
        nota_do_voucher = float(dados_voucher.get('NOTA', 0))

        # 5. Salva a conclusão permanentemente
        Conclusao.objects.create(
            inscricao=inscricao,
            atividade=atividade,
            pontos_ganhos=pontos_totais,
            voucher_bruto=voucher_bruto,
            ra_validado=ra_voucher,
            nota_atribuida=nota_do_voucher
        )

        inscricao.pontos += pontos_totais
        inscricao.save()

        # 6. Atualiza Planilha Google em segundo plano
        if turma.google_sheet_link:
            threading.Thread(
                target=logar_entrega_na_planilha,
                args=(turma.google_sheet_link, atividade.titulo, user.get_full_name(), user.email, pontos_totais, nota_do_voucher)
            ).start()
        
        messages.success(request, f'Atividade concluída! +{pontos_totais} XP e Nota {nota_do_voucher} registrada.')

        # =============================================================================
        #  LÓGICA DE MEDALHAS (AGORA DENTRO DO FLUXO CORRETO)
        # =============================================================================

        # Medalha "10 atividades"
        try:
            total_conclusoes = Conclusao.objects.filter(inscricao__aluno=user).count()
            if total_conclusoes >= 10:
                medalha_robot = Conquista.objects.get(chave='10_atividades')
                ConquistaAluno.objects.get_or_create(aluno=user, conquista=medalha_robot)
        except Conquista.DoesNotExist: pass

        # Medalha "Em cima da hora"
        try:
            if atividade.data_entrega:
                agora = datetime.now()
                if agora.date() == atividade.data_entrega and agora.hour >= 22:
                    medalha_limite = Conquista.objects.get(chave='em_cima_da_hora')
                    ConquistaAluno.objects.get_or_create(aluno=user, conquista=medalha_limite)
        except Conquista.DoesNotExist: pass

        # Medalha "Subiu de Nível"
        try:
            XP_POR_NIVEL = 1000
            nivel_antes = ((inscricao.pontos - pontos_totais) // XP_POR_NIVEL) + 1
            nivel_agora = (inscricao.pontos // XP_POR_NIVEL) + 1
            if nivel_agora > nivel_antes:
                medalha_lvl = Conquista.objects.get(chave='subiu_nivel')
                ConquistaAluno.objects.get_or_create(aluno=user, conquista=medalha_lvl)
        except Conquista.DoesNotExist: pass
        
        # Medalha "The Flash"
        if conclusoes_anteriores == 0:
            try:
                medalha_flash = Conquista.objects.get(chave='flash')
                ConquistaAluno.objects.get_or_create(aluno=user, conquista=medalha_flash)
            except Conquista.DoesNotExist: pass
            
        # Medalha "Líder Isolado"
        try:
            ranking = Inscricao.objects.filter(turma=turma).order_by('-pontos')
            if ranking.count() >= 2:
                if ranking[0].aluno == user and (ranking[0].pontos - ranking[1].pontos) >= 300:
                    medalha_rei = Conquista.objects.get(chave='lider_isolado')
                    ConquistaAluno.objects.get_or_create(aluno=user, conquista=medalha_rei)
        except Exception: pass
            
        return redirect('painel_turma', turma_id=turma.id)

    return redirect('painel_turma', turma_id=turma.id)


@login_required
def alterar_pontos(request, inscricao_id):
    inscricao = get_object_or_404(Inscricao, pk=inscricao_id)
    turma = inscricao.turma

    if request.user != turma.professor:
        messages.error(request, 'Você não tem permissão para esta ação.')
        return redirect('painel_turma', turma_id=turma.id)

    if request.method == 'POST':
        try:
            pontos_para_adicionar = int(request.POST.get('pontos'))
            inscricao.pontos += pontos_para_adicionar
            inscricao.save()
            messages.success(request, f'Pontos de {inscricao.aluno.first_name} atualizados.')
        except (ValueError, TypeError):
            messages.error(request, 'Valor de pontos inválido.')
    
    return redirect('ver_alunos', turma_id=turma.id)


@login_required
def minhas_conquistas(request):
    aluno = request.user
    
    # 1. Dados de Gamificação
    dados_gami = calcular_gamificacao(aluno)
    if not dados_gami:
        # Fallback se não for aluno ou erro
        dados_gami = {'nivel': 0, 'xp_atual': 0, 'xp_meta': 1000, 'porcentagem': 0}

    # 2. Busca e mapeia conquistas
    todas_conquistas = Conquista.objects.all()
    conquistas_do_aluno = ConquistaAluno.objects.filter(aluno=aluno)
    mapa_conquistas = {c.conquista.id: c.data_conquista for c in conquistas_do_aluno}

    lista_final_conquistas = []
    for conquista in todas_conquistas:
        if conquista.id in mapa_conquistas:
            conquista.conquistada = True
            conquista.data_conquista = mapa_conquistas[conquista.id]
        else:
            conquista.conquistada = False
            conquista.data_conquista = None
        lista_final_conquistas.append(conquista)

    # 3. Estatísticas Extras
    total_atividades = Conclusao.objects.filter(inscricao__aluno=aluno).count()
    dias_ativos = Conclusao.objects.filter(inscricao__aluno=aluno).dates('data_conclusao', 'day').count()

    context = {
        'nivel_atual': dados_gami['nivel'],
        'xp_atual': dados_gami['xp_atual'],
        'xp_proximo_nivel': dados_gami['xp_meta'],
        'porcentagem_xp': dados_gami['porcentagem'],
        
        'total_atividades_concluidas': total_atividades,
        'ofensiva': dias_ativos, 
        'total_medalhas': conquistas_do_aluno.count(),
        'total_possivel': todas_conquistas.count(),
        'todas_conquistas': lista_final_conquistas,
    }
    
    return render(request, 'aluno/minhas_conquistas.html', context)
