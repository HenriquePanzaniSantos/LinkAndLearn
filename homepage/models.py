# homepage/models.py

from django.db import models
from django.conf import settings
from django.utils import timezone
import uuid
from django.templatetags.static import static

# --- TURMA ---
class Turma(models.Model):
    google_sheet_link = models.URLField(
        blank=True, null=True, max_length=255, 
        verbose_name="Link da Planilha Google",
        help_text="Gerado automaticamente pelo sistema"
    )
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True)
    professor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='turmas_lecionadas')
    codigo_acesso = models.CharField(max_length=10, blank=True, unique=True, editable=False)
    data_criacao = models.DateTimeField(auto_now_add=True)
    
    # Campo para armazenar a Chave Pública fornecida uma única vez na criação da turma
    chave_publica_pem = models.TextField(
        blank=True, 
        null=True, 
        verbose_name="Chave Pública RSA (PEM)",
        help_text="Chave pública utilizada para validar os vouchers desta turma."
    )

    def save(self, *args, **kwargs):
        if not self.codigo_acesso:
            self.codigo_acesso = str(uuid.uuid4()).replace('-', '')[:8].upper()
        super().save(*args, **kwargs)

    def get_capa(self):
        imagens = ['capa_01.png', 'capa_02.png', 'capa_03.png']
        
        if self.id:
            indice = self.id % len(imagens)
            nome_imagem = imagens[indice]
        else:
            nome_imagem = 'capa_01.png'

        return static(f'assets/imagens/{nome_imagem}')
    
    def __str__(self):
        return self.nome

# --- ATIVIDADE ---
class Atividade(models.Model):
    turma = models.ForeignKey(Turma, on_delete=models.CASCADE, related_name='atividades')
    titulo = models.CharField(max_length=100)
    descricao = models.TextField(blank=True)
    data_entrega = models.DateField(blank=True, null=True, verbose_name="Data de Entrega")
    arquivo = models.FileField(upload_to='atividades/', blank=True, null=True)
    pontos = models.IntegerField(default=0)
    vale_xp = models.BooleanField(default=True)
    codigo_conclusao = models.CharField(max_length=50, blank=True, null=True)
    data_criacao = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.titulo

# --- INSCRICAO ---
class Inscricao(models.Model):
    aluno = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    turma = models.ForeignKey(Turma, on_delete=models.CASCADE)
    data_inscricao = models.DateTimeField(auto_now_add=True)
    pontos = models.IntegerField(default=0)

    class Meta:
        unique_together = ('aluno', 'turma')
        
    def __str__(self):
        return f"{self.aluno} em {self.turma}"

# --- CONCLUSAO ---
class Conclusao(models.Model):
    inscricao = models.ForeignKey(Inscricao, on_delete=models.CASCADE)
    atividade = models.ForeignKey(Atividade, on_delete=models.CASCADE)
    data_conclusao = models.DateTimeField(auto_now_add=True)
    pontos_ganhos = models.IntegerField(default=0)
    
    # Campos para o Voucher e dados descriptografados
    voucher_bruto = models.TextField(blank=True, null=True, verbose_name="Hash do Voucher")
    ra_validado = models.CharField(max_length=50, blank=True, null=True, verbose_name="RA Confirmado")
    nota_atribuida = models.FloatField(blank=True, null=True, verbose_name="Nota")

    class Meta:
        unique_together = ('inscricao', 'atividade')

# --- MEDALHAS ---
class Conquista(models.Model):
    chave = models.CharField(max_length=50, unique=True) 
    titulo = models.CharField(max_length=100)
    descricao = models.TextField()
    imagem_arquivo = models.CharField(max_length=100) 
    
    def __str__(self):
        return self.titulo

class ConquistaAluno(models.Model):
    aluno = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    conquista = models.ForeignKey(Conquista, on_delete=models.CASCADE)
    data_conquista = models.DateTimeField(default=timezone.now)

    class Meta:
        unique_together = ('aluno', 'conquista')
        
    def __str__(self):
        return f"{self.aluno} - {self.conquista.titulo}"