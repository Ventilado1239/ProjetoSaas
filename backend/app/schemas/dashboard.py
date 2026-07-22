import uuid
from datetime import datetime, date
from typing import Literal, Optional, List
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


class StrictInputModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


def validate_phone(value: str) -> str:
    digits = "".join(char for char in value if char.isdigit())
    if not 10 <= len(digits) <= 15:
        raise ValueError("WhatsApp deve conter entre 10 e 15 digitos.")
    return digits

# Tenant
class TenantResponse(BaseModel):
    id: uuid.UUID
    nome: str
    tipo: str
    whatsapp_numero: str
    owner_whatsapp: Optional[str] = None
    evolution_instance_name: Optional[str] = None
    plano: str
    sistema_ativo: bool
    horario_abertura: str
    horario_fechamento: str
    limite_pedido_grande: int
    cor_primaria: str
    logo_url: Optional[str] = None

    class Config:
        from_attributes = True

# ClientePaciente
class ClientePacienteBase(StrictInputModel):
    nome: str = Field(min_length=2, max_length=255)
    whatsapp: str = Field(min_length=10, max_length=50)
    data_nascimento: Optional[date] = None
    convenio: Optional[str] = Field(default=None, max_length=100)

    @field_validator("whatsapp")
    @classmethod
    def normalize_whatsapp(cls, value: str) -> str:
        return validate_phone(value)

    @field_validator("data_nascimento")
    @classmethod
    def birth_date_not_in_future(cls, value: Optional[date]) -> Optional[date]:
        if value and value > date.today():
            raise ValueError("Data de nascimento nao pode estar no futuro.")
        return value

class ClientePacienteCreate(ClientePacienteBase):
    pass

class ClientePacienteResponse(ClientePacienteBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    total_atendimentos: int
    ticket_medio: float
    ultima_consulta: Optional[datetime] = None
    status_reativacao: str

    class Config:
        from_attributes = True

# Preco
class PrecoBase(StrictInputModel):
    qtd_min: int = Field(default=1, ge=1, le=1_000_000)
    qtd_max: int = Field(ge=1, le=1_000_000)
    preco_particular: float = Field(ge=0, le=99999999.99)
    preco_convenio: Optional[float] = Field(default=None, ge=0, le=99999999.99)
    convenio: Optional[str] = Field(default=None, max_length=100)

    @model_validator(mode="after")
    def validate_quantity_range(self):
        if self.qtd_max < self.qtd_min:
            raise ValueError("qtd_max deve ser maior ou igual a qtd_min.")
        return self

class PrecoCreate(PrecoBase):
    pass

class PrecoResponse(PrecoBase):
    id: uuid.UUID
    servico_id: uuid.UUID

    class Config:
        from_attributes = True

# ServicoProduto
class ServicoProdutoBase(StrictInputModel):
    nome: str = Field(min_length=2, max_length=255)
    categoria: Optional[str] = Field(default=None, max_length=100)
    duracao_minutos: Optional[int] = Field(default=None, ge=5, le=1440)
    ativo: bool = True

class ServicoProdutoCreate(ServicoProdutoBase):
    precos: Optional[List[PrecoCreate]] = Field(default=None, max_length=100)

class ServicoProdutoResponse(ServicoProdutoBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    precos: List[PrecoResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True

# ItemAtendimento
class ItemAtendimentoBase(StrictInputModel):
    servico_id: uuid.UUID
    quantidade: int = Field(default=1, ge=1, le=1_000_000)
    preco_unitario: float = Field(ge=0, le=99999999.99)
    personalizacao: Optional[str] = Field(default=None, max_length=2048)
    arquivo_arte_url: Optional[str] = Field(default=None, max_length=1024)
    status_arte: Literal["aguardando", "aprovada", "ajustes", "rejeitada"] = "aguardando"

class ItemAtendimentoCreate(ItemAtendimentoBase):
    pass

class ItemAtendimentoResponse(ItemAtendimentoBase):
    id: uuid.UUID
    atendimento_id: uuid.UUID

    class Config:
        from_attributes = True

# AtendimentoPedido
class AtendimentoPedidoBase(StrictInputModel):
    cliente_id: uuid.UUID
    data_agendamento: datetime
    status: Literal["aguardando", "pendente_aprovacao", "confirmado", "em_producao", "pronto", "realizado", "entregue", "cancelado", "falta", "abandonado"] = "aguardando"
    confirmado: bool = False
    compareceu: Optional[bool] = None
    total: float = Field(default=0.0, ge=0, le=99999999.99)
    pago: bool = False
    lojista_aprovado: bool = False
    origem: Literal["dashboard", "whatsapp", "importacao"] = "dashboard"

    @field_validator("data_agendamento")
    @classmethod
    def require_timezone(cls, value: datetime) -> datetime:
        if value.tzinfo is None or value.utcoffset() is None:
            raise ValueError("data_agendamento deve incluir fuso horario.")
        return value

class AtendimentoPedidoCreate(AtendimentoPedidoBase):
    itens: Optional[List[ItemAtendimentoCreate]] = Field(default=None, max_length=1000)

class AtendimentoPedidoResponse(AtendimentoPedidoBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    cliente_nome: Optional[str] = None
    cliente_whatsapp: Optional[str] = None
    data_atendimento: Optional[datetime] = None
    data_entrega: Optional[datetime] = None
    itens: List[ItemAtendimentoResponse] = Field(default_factory=list)

    class Config:
        from_attributes = True


class AtendimentoStatusUpdate(StrictInputModel):
    status: Optional[Literal["aguardando", "pendente_aprovacao", "confirmado", "em_producao", "pronto", "realizado", "entregue", "cancelado", "falta", "abandonado"]] = None
    pago: Optional[bool] = None
    compareceu: Optional[bool] = None

    @model_validator(mode="after")
    def paid_cannot_be_null(self):
        if "pago" in self.model_fields_set and self.pago is None:
            raise ValueError("pago nao pode ser nulo.")
        return self

# ListaEspera
class ListaEsperaBase(StrictInputModel):
    cliente_id: uuid.UUID
    servico_id: Optional[uuid.UUID] = None
    data_preferida: Optional[datetime] = None

    @field_validator("data_preferida")
    @classmethod
    def preferred_date_requires_timezone(cls, value: Optional[datetime]) -> Optional[datetime]:
        if value is not None and (value.tzinfo is None or value.utcoffset() is None):
            raise ValueError("data_preferida deve incluir fuso horario.")
        return value

class ListaEsperaCreate(ListaEsperaBase):
    pass

class ListaEsperaResponse(ListaEsperaBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    status: str
    cliente_nome: Optional[str] = None
    cliente_whatsapp: Optional[str] = None
    servico_nome: Optional[str] = None

    class Config:
        from_attributes = True

# Configuracao
class ConfiguracaoResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    tenant_nome: Optional[str] = None
    tenant_tipo: Optional[str] = None
    tenant_cor_primaria: Optional[str] = None
    tenant_logo_url: Optional[str] = None
    horario_funcionamento: Optional[str] = None
    limite_pedido_grande: int
    mensagem_boas_vindas: Optional[str] = None
    mensagem_fora_horario: Optional[str] = None
    mensagem_confirmacao: Optional[str] = None
    mensagem_reativacao: Optional[str] = None
    sistema_ativo: bool = True
    owner_whatsapp: Optional[str] = None
    evolution_instance_name: Optional[str] = None

    class Config:
        from_attributes = True

class ConfiguracaoUpdate(StrictInputModel):
    horario_funcionamento: Optional[str] = Field(default=None, max_length=2048)
    limite_pedido_grande: Optional[int] = Field(default=None, ge=1, le=1_000_000)
    mensagem_boas_vindas: Optional[str] = Field(default=None, max_length=1024)
    mensagem_fora_horario: Optional[str] = Field(default=None, max_length=1024)
    mensagem_confirmacao: Optional[str] = Field(default=None, max_length=1024)
    mensagem_reativacao: Optional[str] = Field(default=None, max_length=1024)
    sistema_ativo: Optional[bool] = None
    owner_whatsapp: Optional[str] = Field(default=None, max_length=50)
    evolution_instance_name: Optional[str] = Field(default=None, max_length=120, pattern=r"^[A-Za-z0-9_-]+$")

    @field_validator("owner_whatsapp")
    @classmethod
    def normalize_owner_whatsapp(cls, value: Optional[str]) -> Optional[str]:
        return validate_phone(value) if value else value


# Aprovacao
class AprovacaoResponse(BaseModel):
    id: uuid.UUID
    tenant_id: uuid.UUID
    tipo: str
    atendimento_id: Optional[uuid.UUID] = None
    cliente_id: Optional[uuid.UUID] = None
    detalhes: Optional[str] = None
    status: str
    criado_em: datetime
    atualizado_em: datetime
    
    # Joined info
    cliente_nome: Optional[str] = None
    cliente_whatsapp: Optional[str] = None
    atendimento_total: Optional[float] = None
    atendimento_data: Optional[datetime] = None
    
    class Config:
        from_attributes = True

class AprovacaoProcessRequest(StrictInputModel):
    aprovado: bool

# Dashboard Stats
class DashboardHojeResponse(BaseModel):
    atendimentos_total: int
    atendimentos_confirmados: int
    aprovacoes_pendentes: int
    receita_total: float
    receita_paga: float
    receita_pendente: float
    atendimentos: List[AtendimentoPedidoResponse]

# ROI Report response
class ROIResponse(BaseModel):
    taxa_comparecimento: float
    receita_total: float
    receita_perdida: float
    reativados_count: int
    lista_espera_agendados: int
    impacto_total: float
    mensalidade: float
    roi: float
