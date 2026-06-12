import uuid
from datetime import datetime, date
from typing import Optional, List
from pydantic import BaseModel

# Tenant
class TenantResponse(BaseModel):
    id: uuid.UUID
    nome: str
    tipo: str
    whatsapp_numero: str
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
class ClientePacienteBase(BaseModel):
    nome: str
    whatsapp: str
    data_nascimento: Optional[date] = None
    convenio: Optional[str] = None

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
class PrecoBase(BaseModel):
    qtd_min: int = 1
    qtd_max: int
    preco_particular: float
    preco_convenio: Optional[float] = None
    convenio: Optional[str] = None

class PrecoCreate(PrecoBase):
    pass

class PrecoResponse(PrecoBase):
    id: uuid.UUID
    servico_id: uuid.UUID

    class Config:
        from_attributes = True

# ServicoProduto
class ServicoProdutoBase(BaseModel):
    nome: str
    categoria: Optional[str] = None
    duracao_minutos: Optional[int] = None
    ativo: bool = True

class ServicoProdutoCreate(ServicoProdutoBase):
    precos: Optional[List[PrecoCreate]] = None

class ServicoProdutoResponse(ServicoProdutoBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    precos: List[PrecoResponse] = []

    class Config:
        from_attributes = True

# ItemAtendimento
class ItemAtendimentoBase(BaseModel):
    servico_id: uuid.UUID
    quantidade: int = 1
    preco_unitario: float
    personalizacao: Optional[str] = None
    arquivo_arte_url: Optional[str] = None
    status_arte: str = "aguardando"

class ItemAtendimentoCreate(ItemAtendimentoBase):
    pass

class ItemAtendimentoResponse(ItemAtendimentoBase):
    id: uuid.UUID
    atendimento_id: uuid.UUID

    class Config:
        from_attributes = True

# AtendimentoPedido
class AtendimentoPedidoBase(BaseModel):
    cliente_id: uuid.UUID
    data_agendamento: datetime
    status: str = "aguardando"
    confirmado: bool = False
    compareceu: Optional[bool] = None
    total: float = 0.0
    pago: bool = False
    lojista_aprovado: bool = False
    origem: str = "dashboard"

class AtendimentoPedidoCreate(AtendimentoPedidoBase):
    itens: Optional[List[ItemAtendimentoCreate]] = None

class AtendimentoPedidoResponse(AtendimentoPedidoBase):
    id: uuid.UUID
    tenant_id: uuid.UUID
    cliente_nome: Optional[str] = None
    cliente_whatsapp: Optional[str] = None
    itens: List[ItemAtendimentoResponse] = []

    class Config:
        from_attributes = True

# ListaEspera
class ListaEsperaBase(BaseModel):
    cliente_id: uuid.UUID
    servico_id: Optional[uuid.UUID] = None
    data_preferida: Optional[datetime] = None

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
    horario_funcionamento: Optional[str] = None
    limite_pedido_grande: int
    mensagem_boas_vindas: Optional[str] = None
    mensagem_fora_horario: Optional[str] = None
    mensagem_confirmacao: Optional[str] = None
    mensagem_reativacao: Optional[str] = None
    sistema_ativo: bool = True

    class Config:
        from_attributes = True

class ConfiguracaoUpdate(BaseModel):
    horario_funcionamento: Optional[str] = None
    limite_pedido_grande: Optional[int] = None
    mensagem_boas_vindas: Optional[str] = None
    mensagem_fora_horario: Optional[str] = None
    mensagem_confirmacao: Optional[str] = None
    mensagem_reativacao: Optional[str] = None
    sistema_ativo: Optional[bool] = None


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

class AprovacaoProcessRequest(BaseModel):
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
