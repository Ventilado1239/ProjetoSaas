import uuid
from datetime import datetime, date
from typing import Optional
from sqlalchemy import String, Integer, Boolean, Numeric, DateTime, Date, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.types import TypeDecorator, LargeBinary
from app.database import Base
from app.config import settings

class PGPEncryptedText(TypeDecorator):
    """
    Encrypts string data transparently using pgp_sym_encrypt on write
    and pgp_sym_decrypt on read at the database level using pgcrypto.
    """
    impl = String
    cache_ok = False

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.key = settings.data_encryption_key

    def bind_expression(self, bindvalue):
        if bindvalue is None:
            return None
        return func.pgp_sym_encrypt(bindvalue, self.key)

    def column_expression(self, col):
        if col is None:
            return None
        return func.pgp_sym_decrypt(col, self.key)

    @property
    def python_type(self):
        return str


class Tenant(Base):
    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    tipo: Mapped[str] = mapped_column(String(50), nullable=False)  # 'clinica' | 'loja'
    whatsapp_numero: Mapped[str] = mapped_column(String(50), nullable=False)
    owner_whatsapp: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    evolution_instance_name: Mapped[Optional[str]] = mapped_column(String(120), nullable=True, unique=True)
    plano: Mapped[str] = mapped_column(String(50), nullable=False, default="starter")  # 'starter' | 'pro' | 'premium'
    sistema_ativo: Mapped[bool] = mapped_column(Boolean, default=True)  # KILL SWITCH
    horario_abertura: Mapped[str] = mapped_column(String(5), default="08:00")
    horario_fechamento: Mapped[str] = mapped_column(String(5), default="18:00")
    limite_pedido_grande: Mapped[int] = mapped_column(Integer, default=10)
    cor_primaria: Mapped[str] = mapped_column(String(7), default="#2563eb")
    logo_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    responsavel_nome: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    responsavel_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    mensalidade: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    pagamento_status: Mapped[str] = mapped_column(String(50), default="em_dia")
    crm_stage: Mapped[str] = mapped_column(String(50), default="ativo")
    proximo_vencimento: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    asaas_customer_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, unique=True)
    asaas_subscription_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, unique=True)
    observacoes: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)


class MasterAdmin(Base):
    __tablename__ = "master_admins"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    ultimo_login_em: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class MasterLead(Base):
    __tablename__ = "master_leads"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    nome_clinica: Mapped[str] = mapped_column(String(255), nullable=False)
    responsavel_nome: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    responsavel_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    whatsapp: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    etapa: Mapped[str] = mapped_column(String(50), default="lead")
    valor_potencial: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    proxima_acao: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    observacoes: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class MasterAuditLog(Base):
    __tablename__ = "master_audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    admin_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("master_admins.id", ondelete="SET NULL"), nullable=True)
    acao: Mapped[str] = mapped_column(String(80), nullable=False)
    entidade: Mapped[str] = mapped_column(String(80), nullable=False)
    entidade_id: Mapped[Optional[uuid.UUID]] = mapped_column(nullable=True)
    detalhes: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)
    ip_origem: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class Usuario(Base):
    __tablename__ = "usuarios"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    senha_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    perfil: Mapped[str] = mapped_column(String(50), nullable=False)  # 'dono' | 'medico' | 'recepcionista' | 'funcionario'
    ativo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    token_version: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

class ClientePaciente(Base):
    __tablename__ = "clientes_pacientes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    nome: Mapped[str] = mapped_column(PGPEncryptedText, nullable=False)
    whatsapp: Mapped[str] = mapped_column(String(50), nullable=False)  # unique por tenant
    data_nascimento: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    convenio: Mapped[Optional[str]] = mapped_column(PGPEncryptedText, nullable=True)
    total_atendimentos: Mapped[int] = mapped_column(Integer, default=0)
    ticket_medio: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0)
    ultima_consulta: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status_reativacao: Mapped[str] = mapped_column(String(50), default="ativo")  # 'ativo' | 'inativo_3m' | 'inativo_6m' | 'inativo_12m' | 'reativado'
    reativado_em: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("tenant_id", "whatsapp", name="uq_tenant_whatsapp"),
    )

class ServicoProduto(Base):
    __tablename__ = "servicos_produtos"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    nome: Mapped[str] = mapped_column(String(255), nullable=False)
    categoria: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    duracao_minutos: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    ativo: Mapped[bool] = mapped_column(Boolean, default=True)

class Preco(Base):
    __tablename__ = "precos"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    servico_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("servicos_produtos.id", ondelete="CASCADE"), nullable=False)
    qtd_min: Mapped[int] = mapped_column(Integer, default=1)
    qtd_max: Mapped[int] = mapped_column(Integer)
    preco_particular: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    preco_convenio: Mapped[Optional[float]] = mapped_column(Numeric(10, 2), nullable=True)
    convenio: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

class AtendimentoPedido(Base):
    __tablename__ = "atendimentos_pedidos"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    cliente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clientes_pacientes.id", ondelete="CASCADE"), nullable=False)
    data_agendamento: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    data_atendimento: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    data_entrega: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="aguardando")  # 'aguardando' | 'confirmado' | 'em_producao' | 'pronto' | 'realizado' | 'entregue' | 'cancelado' | 'falta' | 'abandonado'
    confirmado: Mapped[bool] = mapped_column(Boolean, default=False)
    compareceu: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    total: Mapped[float] = mapped_column(Numeric(10, 2), default=0.0)
    pago: Mapped[bool] = mapped_column(Boolean, default=False)
    lojista_aprovado: Mapped[bool] = mapped_column(Boolean, default=False)
    origem: Mapped[str] = mapped_column(String(50), default="dashboard")  # 'whatsapp' | 'dashboard'

class ItemAtendimento(Base):
    __tablename__ = "itens_atendimento"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    atendimento_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("atendimentos_pedidos.id", ondelete="CASCADE"), nullable=False)
    servico_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("servicos_produtos.id", ondelete="CASCADE"), nullable=False)
    quantidade: Mapped[int] = mapped_column(Integer, default=1)
    preco_unitario: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)
    personalizacao: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    arquivo_arte_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    status_arte: Mapped[str] = mapped_column(String(50), default="aguardando")  # 'aguardando' | 'enviado' | 'aprovado' | 'reprovado'

class ListaEspera(Base):
    __tablename__ = "lista_espera"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    cliente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clientes_pacientes.id", ondelete="CASCADE"), nullable=False)
    servico_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("servicos_produtos.id", ondelete="SET NULL"), nullable=True)
    data_preferida: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="aguardando")  # 'aguardando' | 'notificado' | 'agendado' | 'expirado'
    agendado_em: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

class LogMensagem(Base):
    __tablename__ = "logs_mensagens"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    cliente_whatsapp: Mapped[str] = mapped_column(String(50), nullable=False)
    direcao: Mapped[str] = mapped_column(String(10), nullable=False)  # 'entrada' | 'saida'
    mensagem: Mapped[str] = mapped_column(String(4000), nullable=False)
    tipo: Mapped[str] = mapped_column(String(50), default="texto")  # 'texto' | 'audio' | 'imagem' | 'documento'
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class Configuracao(Base):
    __tablename__ = "configuracoes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), unique=True, nullable=False)
    horario_funcionamento: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True) # JSON-string representation
    limite_pedido_grande: Mapped[int] = mapped_column(Integer, default=10)
    mensagem_boas_vindas: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    mensagem_fora_horario: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    mensagem_confirmacao: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    mensagem_reativacao: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)

class TokenBlacklist(Base):
    __tablename__ = "token_blacklist"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    token: Mapped[str] = mapped_column(String(512), unique=True, nullable=False, index=True)
    revogado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    expira_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class WebhookEvent(Base):
    __tablename__ = "webhook_events"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    provider: Mapped[str] = mapped_column(String(30), nullable=False)
    event_id: Mapped[str] = mapped_column(String(255), nullable=False)
    tenant_id: Mapped[Optional[uuid.UUID]] = mapped_column(nullable=True)
    recebido_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    __table_args__ = (
        UniqueConstraint("provider", "event_id", name="uq_webhook_provider_event"),
    )

class EstadoConversa(Base):
    __tablename__ = "estados_conversa"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    cliente_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("clientes_pacientes.id", ondelete="CASCADE"), unique=True, nullable=False)
    etapa_atual: Mapped[str] = mapped_column(String(50), default="menu")  # 'menu' | 'aguardando_produto' | 'aguardando_quantidade' | etc.
    dados_acumulados: Mapped[Optional[str]] = mapped_column(String(2048), nullable=True)  # JSON representation of selected inputs
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class Aprovacao(Base):
    __tablename__ = "aprovacoes"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    tipo: Mapped[str] = mapped_column(String(50), nullable=False)  # 'confirmacao_48h' | 'pedido_grande' | 'cliente_sumiu'
    atendimento_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("atendimentos_pedidos.id", ondelete="CASCADE"), nullable=True)
    cliente_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("clientes_pacientes.id", ondelete="CASCADE"), nullable=True)
    detalhes: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    status: Mapped[str] = mapped_column(String(50), default="pendente")  # 'pendente' | 'aprovado' | 'recusado' | 'resolvido'
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    atualizado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

class LogAuditoria(Base):
    __tablename__ = "logs_auditoria"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    tenant_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False)
    usuario_id: Mapped[Optional[uuid.UUID]] = mapped_column(ForeignKey("usuarios.id", ondelete="SET NULL"), nullable=True)
    usuario_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    acao: Mapped[str] = mapped_column(String(50), nullable=False)  # 'INSERT' | 'UPDATE' | 'DELETE'
    tabela: Mapped[str] = mapped_column(String(50), nullable=False)  # 'clientes_pacientes' | 'atendimentos_pedidos'
    registro_id: Mapped[uuid.UUID] = mapped_column(nullable=False)
    valores_antigos: Mapped[Optional[str]] = mapped_column(String(4000), nullable=True)  # JSON-string representation of old values
    valores_novos: Mapped[Optional[str]] = mapped_column(String(4000), nullable=True)  # JSON-string representation of new values
    criado_em: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
