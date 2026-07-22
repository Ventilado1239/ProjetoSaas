import uuid
import json
import io
from datetime import datetime, date, time, timezone
from typing import List, Literal, Optional
from zoneinfo import ZoneInfo

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import select, func, text, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.database import get_db
from app.config import settings
from app.models.models import (
    Usuario, Tenant, ClientePaciente, ServicoProduto, Preco,
    AtendimentoPedido, ItemAtendimento, ListaEspera, Aprovacao,
    Configuracao, LogMensagem, LogAuditoria
)
from app.dependencies import get_current_user, get_tenant_id, require_roles
from app.schemas.dashboard import (
    DashboardHojeResponse, AtendimentoPedidoResponse, AtendimentoPedidoCreate,
    ClientePacienteResponse, ClientePacienteCreate, ServicoProdutoResponse,
    ServicoProdutoCreate, PrecoResponse, PrecoCreate, ListaEsperaResponse,
    ListaEsperaCreate, ConfiguracaoResponse, ConfiguracaoUpdate,
    AprovacaoResponse, AprovacaoProcessRequest, ROIResponse, ItemAtendimentoResponse,
    AtendimentoStatusUpdate
)
from app.services.pos_atendimento_service import agendar_pos_atendimento
from app.services.aprovacao_service import processar_decisao_dono
from app.services.pdf_service import gerar_pdf_fechamento_diario, gerar_pdf_roi_mensal
from app.schemas.auth import OperatorCreate, OperatorResponse
from app.utils.security import get_password_hash, validate_password_strength

router = APIRouter(tags=["dashboard"])

@router.get("/dashboard/hoje", response_model=DashboardHojeResponse)
async def get_dashboard_hoje(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    tz = ZoneInfo("America/Sao_Paulo")
    now = datetime.now(tz)
    start_of_day = datetime.combine(now.date(), time.min).replace(tzinfo=tz)
    end_of_day = datetime.combine(now.date(), time.max).replace(tzinfo=tz)

    # 1. Fetch appointments for today
    stmt = select(AtendimentoPedido, ClientePaciente.nome, ClientePaciente.whatsapp).join(
        ClientePaciente, AtendimentoPedido.cliente_id == ClientePaciente.id
    ).where(
        AtendimentoPedido.data_agendamento >= start_of_day,
        AtendimentoPedido.data_agendamento <= end_of_day
    ).order_by(AtendimentoPedido.data_agendamento.asc())

    results = (await db.execute(stmt)).all()

    atendimentos = []
    atendimento_ids = []
    
    for row in results:
        appt, c_nome, c_whatsapp = row
        atendimento_ids.append(appt.id)
        atendimentos.append({
            "appt": appt,
            "c_nome": c_nome,
            "c_whatsapp": c_whatsapp,
            "itens": []
        })

    # Fetch items for today's appointments
    if atendimento_ids:
        items_stmt = select(ItemAtendimento).where(ItemAtendimento.atendimento_id.in_(atendimento_ids))
        items = (await db.execute(items_stmt)).scalars().all()
        
        # Map items to appointments
        items_by_appt = {}
        for item in items:
            if item.atendimento_id not in items_by_appt:
                items_by_appt[item.atendimento_id] = []
            items_by_appt[item.atendimento_id].append(item)

        for a in atendimentos:
            appt_id = a["appt"].id
            if appt_id in items_by_appt:
                a["itens"] = [
                    ItemAtendimentoResponse(
                        id=i.id,
                        atendimento_id=i.atendimento_id,
                        servico_id=i.servico_id,
                        quantidade=i.quantidade,
                        preco_unitario=float(i.preco_unitario),
                        personalizacao=i.personalizacao,
                        arquivo_arte_url=i.arquivo_arte_url,
                        status_arte=i.status_arte
                    )
                    for i in items_by_appt[appt_id]
                ]

    # Calculate metrics
    atendimentos_total = len(atendimentos)
    atendimentos_confirmados = sum(
        1 for a in atendimentos 
        if a["appt"].confirmado or a["appt"].status in ["confirmado", "em_producao", "pronto", "realizado", "entregue"]
    )
    
    # 2. Fetch pending approvals
    aprov_stmt = select(func.count(Aprovacao.id)).where(Aprovacao.status == "pendente")
    aprovacoes_pendentes = (await db.execute(aprov_stmt)).scalar() or 0

    # 3. Revenue stats
    receita_total = sum(float(a["appt"].total) for a in atendimentos)
    receita_paga = sum(float(a["appt"].total) for a in atendimentos if a["appt"].pago)
    receita_pendente = receita_total - receita_paga

    # Build response list
    atendimentos_res = [
        AtendimentoPedidoResponse(
            id=a["appt"].id,
            tenant_id=a["appt"].tenant_id,
            cliente_id=a["appt"].cliente_id,
            cliente_nome=a["c_nome"],
            cliente_whatsapp=a["c_whatsapp"],
            data_agendamento=a["appt"].data_agendamento,
            data_atendimento=a["appt"].data_atendimento,
            data_entrega=a["appt"].data_entrega,
            status=a["appt"].status,
            confirmado=a["appt"].confirmado,
            compareceu=a["appt"].compareceu,
            total=float(a["appt"].total),
            pago=a["appt"].pago,
            lojista_aprovado=a["appt"].lojista_aprovado,
            origem=a["appt"].origem,
            itens=a["itens"]
        )
        for a in atendimentos
    ]

    return DashboardHojeResponse(
        atendimentos_total=atendimentos_total,
        atendimentos_confirmados=atendimentos_confirmados,
        aprovacoes_pendentes=aprovacoes_pendentes,
        receita_total=receita_total,
        receita_paga=receita_paga,
        receita_pendente=receita_pendente,
        atendimentos=atendimentos_res
    )

@router.get("/dashboard/roi", response_model=ROIResponse)
async def get_dashboard_roi(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Fetch tenant
    tenant = await db.get(Tenant, current_user.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado.")

    # Total appointments (comparecimento count)
    count_stmt = select(
        func.count(AtendimentoPedido.id),
        func.sum(AtendimentoPedido.total)
    ).where(AtendimentoPedido.status.in_(["realizado", "entregue"]))
    res = (await db.execute(count_stmt)).first()
    realizados_count = res[0] or 0
    receita_total = float(res[1] or 0.0)

    # Taxa de comparecimento
    # comparecimento = realizados / (realizados + faltas)
    faltas_stmt = select(func.count(AtendimentoPedido.id)).where(AtendimentoPedido.status == "falta")
    faltas_count = (await db.execute(faltas_stmt)).scalar() or 0
    total_comp_denom = realizados_count + faltas_count
    taxa_comparecimento = (realizados_count / total_comp_denom * 100) if total_comp_denom > 0 else 100.0

    # Receita perdida com faltas
    receita_perdida_stmt = select(func.sum(AtendimentoPedido.total)).where(AtendimentoPedido.status == "falta")
    receita_perdida = float((await db.execute(receita_perdida_stmt)).scalar() or 0.0)

    # Reativados
    reativados_stmt = select(func.count(ClientePaciente.id)).where(ClientePaciente.status_reativacao == "reativado")
    reativados_count = (await db.execute(reativados_stmt)).scalar() or 0

    # Lista de espera agendados
    lista_espera_stmt = select(func.count(ListaEspera.id)).where(ListaEspera.status == "agendado")
    lista_espera_agendados = (await db.execute(lista_espera_stmt)).scalar() or 0

    # Calculate average ticket to estimate recovered revenue
    ticket_avg_stmt = select(func.avg(AtendimentoPedido.total)).where(AtendimentoPedido.status.in_(["realizado", "entregue"]))
    ticket_medio = float((await db.execute(ticket_avg_stmt)).scalar() or 150.0)

    # Impacto = (reativados * ticket_medio) + (lista_espera * ticket_medio)
    impacto_total = (reativados_count * ticket_medio) + (lista_espera_agendados * ticket_medio)

    # Mensalidade
    mensalidade_map = {"starter": 99.0, "pro": 199.0, "premium": 399.0}
    mensalidade = mensalidade_map.get(tenant.plano, 199.0)

    roi = (impacto_total / mensalidade) if mensalidade > 0 else 0.0

    return ROIResponse(
        taxa_comparecimento=taxa_comparecimento,
        receita_total=receita_total,
        receita_perdida=receita_perdida,
        reativados_count=reativados_count,
        lista_espera_agendados=lista_espera_agendados,
        impacto_total=impacto_total,
        mensalidade=mensalidade,
        roi=roi
    )

@router.get("/clientes", response_model=List[ClientePacienteResponse])
async def list_clientes(
    search: Optional[str] = Query(None, max_length=100),
    status_reativacao: Optional[Literal["ativo", "inativo_3m", "inativo_6m", "inativo_12m", "reativado"]] = None,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0, le=1_000_000),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(ClientePaciente)
    if search:
        decrypted_name = func.pgp_sym_decrypt(
            ClientePaciente.__table__.c.nome,
            settings.data_encryption_key,
        )
        stmt = stmt.where(
            (decrypted_name.ilike(f"%{search}%")) |
            (ClientePaciente.whatsapp.like(f"%{search}%"))
        )
    if status_reativacao:
        stmt = stmt.where(ClientePaciente.status_reativacao == status_reativacao)
        
    stmt = stmt.order_by(ClientePaciente.nome.asc()).limit(limit).offset(offset)
    results = (await db.execute(stmt)).scalars().all()
    return results

@router.post("/clientes", response_model=ClientePacienteResponse, status_code=201)
async def create_cliente(
    cliente_data: ClientePacienteCreate,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Verify unique constraint by checking if whatsapp exists for this tenant
    exist_stmt = select(ClientePaciente).where(ClientePaciente.whatsapp == cliente_data.whatsapp)
    exists = (await db.execute(exist_stmt)).scalar_one_or_none()
    if exists:
        raise HTTPException(
            status_code=400,
            detail="Já existe um cliente cadastrado com este WhatsApp neste tenant."
        )

    cliente = ClientePaciente(
        id=uuid.uuid4(),
        tenant_id=current_user.tenant_id,
        nome=cliente_data.nome,
        whatsapp=cliente_data.whatsapp,
        data_nascimento=cliente_data.data_nascimento,
        convenio=cliente_data.convenio,
        total_atendimentos=0,
        ticket_medio=0.0,
        status_reativacao="ativo"
    )
    db.add(cliente)
    await db.commit()
    await db.refresh(cliente)
    return cliente

@router.get("/clientes/{id}", response_model=ClientePacienteResponse)
async def get_cliente(
    id: uuid.UUID,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    cliente = await db.get(ClientePaciente, id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")
    return cliente

@router.put("/clientes/{id}", response_model=ClientePacienteResponse)
async def update_cliente(
    id: uuid.UUID,
    cliente_data: ClientePacienteCreate,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    cliente = await db.get(ClientePaciente, id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")

    duplicate = (await db.execute(
        select(ClientePaciente.id).where(
            ClientePaciente.whatsapp == cliente_data.whatsapp,
            ClientePaciente.id != id,
        )
    )).scalar_one_or_none()
    if duplicate:
        raise HTTPException(status_code=400, detail="Já existe um cliente cadastrado com este WhatsApp neste tenant.")
        
    cliente.nome = cliente_data.nome
    cliente.whatsapp = cliente_data.whatsapp
    cliente.data_nascimento = cliente_data.data_nascimento
    cliente.convenio = cliente_data.convenio
    
    await db.commit()
    await db.refresh(cliente)
    return cliente

@router.delete("/clientes/{id}/lgpd", status_code=204)
async def delete_cliente_lgpd(
    id: uuid.UUID,
    current_user: Usuario = Depends(require_roles("dono")),
    db: AsyncSession = Depends(get_db)
):
    """LGPD compliant erasure of client data (Right to be Forgotten)"""
    cliente = await db.get(ClientePaciente, id)
    if not cliente:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")

    # 1. Delete all message logs for this whatsapp number to ensure right to be forgotten
    await db.execute(delete(LogMensagem).where(LogMensagem.cliente_whatsapp == cliente.whatsapp))

    # 2. Mark the client object with a transient flag for the audit event listener to anonymize the values
    cliente._lgpd_delete = True

    # 3. Delete the client. Cascade delete handles appointments, waitlist, and conversation states
    await db.delete(cliente)
    await db.commit()
    return None

@router.get("/atendimentos", response_model=List[AtendimentoPedidoResponse])
async def list_atendimentos(
    data_inicio: Optional[datetime] = None,
    data_fim: Optional[datetime] = None,
    status: Optional[Literal["aguardando", "pendente_aprovacao", "confirmado", "em_producao", "pronto", "realizado", "entregue", "cancelado", "falta", "abandonado"]] = None,
    cliente_id: Optional[uuid.UUID] = None,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(AtendimentoPedido, ClientePaciente.nome, ClientePaciente.whatsapp).join(
        ClientePaciente, AtendimentoPedido.cliente_id == ClientePaciente.id
    )

    if data_inicio:
        stmt = stmt.where(AtendimentoPedido.data_agendamento >= data_inicio)
    if data_fim:
        stmt = stmt.where(AtendimentoPedido.data_agendamento <= data_fim)
    if status:
        stmt = stmt.where(AtendimentoPedido.status == status)
    if cliente_id:
        stmt = stmt.where(AtendimentoPedido.cliente_id == cliente_id)

    stmt = stmt.order_by(AtendimentoPedido.data_agendamento.desc())

    results = (await db.execute(stmt)).all()

    atendimentos = []
    atendimento_ids = []
    for row in results:
        appt, c_nome, c_whatsapp = row
        atendimento_ids.append(appt.id)
        atendimentos.append({
            "appt": appt,
            "c_nome": c_nome,
            "c_whatsapp": c_whatsapp,
            "itens": []
        })

    if atendimento_ids:
        items_stmt = select(ItemAtendimento).where(ItemAtendimento.atendimento_id.in_(atendimento_ids))
        items = (await db.execute(items_stmt)).scalars().all()
        items_by_appt = {}
        for item in items:
            if item.atendimento_id not in items_by_appt:
                items_by_appt[item.atendimento_id] = []
            items_by_appt[item.atendimento_id].append(item)

        for a in atendimentos:
            appt_id = a["appt"].id
            if appt_id in items_by_appt:
                a["itens"] = [
                    ItemAtendimentoResponse(
                        id=i.id,
                        atendimento_id=i.atendimento_id,
                        servico_id=i.servico_id,
                        quantidade=i.quantidade,
                        preco_unitario=float(i.preco_unitario),
                        personalizacao=i.personalizacao,
                        arquivo_arte_url=i.arquivo_arte_url,
                        status_arte=i.status_arte
                    )
                    for i in items_by_appt[appt_id]
                ]

    return [
        AtendimentoPedidoResponse(
            id=a["appt"].id,
            tenant_id=a["appt"].tenant_id,
            cliente_id=a["appt"].cliente_id,
            cliente_nome=a["c_nome"],
            cliente_whatsapp=a["c_whatsapp"],
            data_agendamento=a["appt"].data_agendamento,
            data_atendimento=a["appt"].data_atendimento,
            data_entrega=a["appt"].data_entrega,
            status=a["appt"].status,
            confirmado=a["appt"].confirmado,
            compareceu=a["appt"].compareceu,
            total=float(a["appt"].total),
            pago=a["appt"].pago,
            lojista_aprovado=a["appt"].lojista_aprovado,
            origem=a["appt"].origem,
            itens=a["itens"]
        )
        for a in atendimentos
    ]

@router.post("/atendimentos", response_model=AtendimentoPedidoResponse, status_code=201)
async def create_atendimento(
    appt_data: AtendimentoPedidoCreate,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Verify client exists
    client = await db.get(ClientePaciente, appt_data.cliente_id)
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")

    if appt_data.itens:
        requested_service_ids = {item.servico_id for item in appt_data.itens}
        existing_service_ids = set((await db.execute(
            select(ServicoProduto.id).where(ServicoProduto.id.in_(requested_service_ids))
        )).scalars().all())
        if existing_service_ids != requested_service_ids:
            raise HTTPException(status_code=404, detail="Um ou mais serviços/produtos não foram encontrados.")

    # Create appointment
    appt = AtendimentoPedido(
        id=uuid.uuid4(),
        tenant_id=current_user.tenant_id,
        cliente_id=appt_data.cliente_id,
        data_agendamento=appt_data.data_agendamento,
        status=appt_data.status,
        confirmado=appt_data.confirmado,
        compareceu=appt_data.compareceu,
        total=appt_data.total,
        pago=appt_data.pago,
        lojista_aprovado=appt_data.lojista_aprovado,
        origem=appt_data.origem
    )
    db.add(appt)
    await db.flush()

    # Create items if provided
    created_items = []
    if appt_data.itens:
        calculated_total = 0.0
        for item_in in appt_data.itens:
            item = ItemAtendimento(
                id=uuid.uuid4(),
                tenant_id=current_user.tenant_id,
                atendimento_id=appt.id,
                servico_id=item_in.servico_id,
                quantidade=item_in.quantidade,
                preco_unitario=item_in.preco_unitario,
                personalizacao=item_in.personalizacao,
                arquivo_arte_url=item_in.arquivo_arte_url,
                status_arte=item_in.status_arte
            )
            db.add(item)
            created_items.append(item)
            calculated_total += item_in.quantidade * item_in.preco_unitario
        
        # Override total if it wasn't specified
        if appt.total == 0.0:
            appt.total = calculated_total
        
        await db.flush()

    # Update client stats
    client.total_atendimentos += 1
    # Simple rolling ticket calculation
    total_val = float(appt.total)
    client.ticket_medio = float(
        (float(client.ticket_medio) * (client.total_atendimentos - 1) + total_val) / client.total_atendimentos
    )
    db.add(client)
    await db.commit()

    return AtendimentoPedidoResponse(
        id=appt.id,
        tenant_id=appt.tenant_id,
        cliente_id=appt.cliente_id,
        cliente_nome=client.nome,
        cliente_whatsapp=client.whatsapp,
        data_agendamento=appt.data_agendamento,
        data_atendimento=appt.data_atendimento,
        data_entrega=appt.data_entrega,
        status=appt.status,
        confirmado=appt.confirmado,
        compareceu=appt.compareceu,
        total=float(appt.total),
        pago=appt.pago,
        lojista_aprovado=appt.lojista_aprovado,
        origem=appt.origem,
        itens=[
            ItemAtendimentoResponse(
                id=i.id,
                atendimento_id=i.atendimento_id,
                servico_id=i.servico_id,
                quantidade=i.quantidade,
                preco_unitario=float(i.preco_unitario),
                personalizacao=i.personalizacao,
                arquivo_arte_url=i.arquivo_arte_url,
                status_arte=i.status_arte
            ) for i in created_items
        ]
    )

@router.patch("/atendimentos/{id}/status", response_model=AtendimentoPedidoResponse)
async def patch_atendimento_status(
    id: uuid.UUID,
    status_update: AtendimentoStatusUpdate,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    appt = await db.get(AtendimentoPedido, id)
    if not appt:
        raise HTTPException(status_code=404, detail="Atendimento/Pedido não encontrado.")

    old_status = appt.status
    new_status = status_update.status
    
    if new_status:
        appt.status = new_status
        if new_status in ["realizado", "entregue"]:
            appt.compareceu = True
            if new_status == "realizado":
                appt.data_atendimento = datetime.now(timezone.utc)
            else:
                appt.data_entrega = datetime.now(timezone.utc)
        elif new_status == "falta":
            appt.compareceu = False
            
    if "pago" in status_update.model_fields_set:
        appt.pago = status_update.pago
    if "compareceu" in status_update.model_fields_set:
        appt.compareceu = status_update.compareceu

    await db.commit()
    await db.refresh(appt)

    # Trigger post-care message (30m delay) if status changed to completed (realizado/entregue)
    if new_status in ["realizado", "entregue"] and old_status not in ["realizado", "entregue"]:
        agendar_pos_atendimento(current_user.tenant_id, appt.id)

    # Fetch client details to return response
    client = await db.get(ClientePaciente, appt.cliente_id)
    
    return AtendimentoPedidoResponse(
        id=appt.id,
        tenant_id=appt.tenant_id,
        cliente_id=appt.cliente_id,
        cliente_nome=client.nome if client else None,
        cliente_whatsapp=client.whatsapp if client else None,
        data_agendamento=appt.data_agendamento,
        data_atendimento=appt.data_atendimento,
        data_entrega=appt.data_entrega,
        status=appt.status,
        confirmado=appt.confirmado,
        compareceu=appt.compareceu,
        total=float(appt.total),
        pago=appt.pago,
        lojista_aprovado=appt.lojista_aprovado,
        origem=appt.origem,
        itens=[]
    )

@router.get("/atendimentos/aprovacoes", response_model=List[AprovacaoResponse])
async def list_aprovacoes(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Query pending/all approvals joined with client and appointment details
    stmt = select(
        Aprovacao,
        ClientePaciente.nome,
        ClientePaciente.whatsapp,
        AtendimentoPedido.total,
        AtendimentoPedido.data_agendamento
    ).outerjoin(
        ClientePaciente, Aprovacao.cliente_id == ClientePaciente.id
    ).outerjoin(
        AtendimentoPedido, Aprovacao.atendimento_id == AtendimentoPedido.id
    ).where(
        Aprovacao.status == "pendente"
    ).order_by(Aprovacao.criado_em.asc())

    results = (await db.execute(stmt)).all()
    
    return [
        AprovacaoResponse(
            id=row[0].id,
            tenant_id=row[0].tenant_id,
            tipo=row[0].tipo,
            atendimento_id=row[0].atendimento_id,
            cliente_id=row[0].cliente_id,
            detalhes=row[0].detalhes,
            status=row[0].status,
            criado_em=row[0].criado_em,
            atualizado_em=row[0].atualizado_em,
            cliente_nome=row[1],
            cliente_whatsapp=row[2],
            atendimento_total=float(row[3]) if row[3] is not None else None,
            atendimento_data=row[4]
        )
        for row in results
    ]

@router.post("/atendimentos/aprovacoes/{id}/processar")
async def processar_aprovacao(
    id: uuid.UUID,
    payload: AprovacaoProcessRequest,
    current_user: Usuario = Depends(require_roles("dono")),
    db: AsyncSession = Depends(get_db)
):
    aprv = await db.get(Aprovacao, id)
    if not aprv:
        raise HTTPException(status_code=404, detail="Aprovação não encontrada.")

    tenant = await db.get(Tenant, current_user.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado.")

    decisao = "aprovar" if payload.aprovado else "recusar"
    await processar_decisao_dono(db, tenant, aprv, decisao)
    await db.commit()
    
    return {"status": "success", "message": f"Decisão '{decisao}' processada com sucesso."}

@router.get("/servicos", response_model=List[ServicoProdutoResponse])
async def list_servicos(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(ServicoProduto).order_by(ServicoProduto.nome.asc())
    servicos = (await db.execute(stmt)).scalars().all()

    if not servicos:
        return []

    # Batch query all prices for these services to eliminate N+1 queries
    servico_ids = [s.id for s in servicos]
    prices_stmt = select(Preco).where(Preco.servico_id.in_(servico_ids))
    prices_all = (await db.execute(prices_stmt)).scalars().all()

    # Group prices by service_id
    prices_by_service = {}
    for p in prices_all:
        if p.servico_id not in prices_by_service:
            prices_by_service[p.servico_id] = []
        prices_by_service[p.servico_id].append(p)

    # Load related price ranges
    res = []
    for s in servicos:
        prices = prices_by_service.get(s.id, [])
        res.append(
            ServicoProdutoResponse(
                id=s.id,
                tenant_id=s.tenant_id,
                nome=s.nome,
                categoria=s.categoria,
                duracao_minutos=s.duracao_minutos,
                ativo=s.ativo,
                precos=[
                    PrecoResponse(
                        id=p.id,
                        servico_id=p.servico_id,
                        qtd_min=p.qtd_min,
                        qtd_max=p.qtd_max,
                        preco_particular=float(p.preco_particular),
                        preco_convenio=float(p.preco_convenio) if p.preco_convenio is not None else None,
                        convenio=p.convenio
                    )
                    for p in prices
                ]
            )
        )
    return res

@router.post("/servicos", response_model=ServicoProdutoResponse, status_code=201)
async def create_servico(
    servico_data: ServicoProdutoCreate,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    s = ServicoProduto(
        id=uuid.uuid4(),
        tenant_id=current_user.tenant_id,
        nome=servico_data.nome,
        categoria=servico_data.categoria,
        duracao_minutos=servico_data.duracao_minutos,
        ativo=servico_data.ativo
    )
    db.add(s)
    await db.flush()

    created_prices = []
    if servico_data.precos:
        for p_data in servico_data.precos:
            p = Preco(
                id=uuid.uuid4(),
                tenant_id=current_user.tenant_id,
                servico_id=s.id,
                qtd_min=p_data.qtd_min,
                qtd_max=p_data.qtd_max,
                preco_particular=p_data.preco_particular,
                preco_convenio=p_data.preco_convenio,
                convenio=p_data.convenio
            )
            db.add(p)
            created_prices.append(p)
        await db.flush()
        
    await db.commit()
    
    return ServicoProdutoResponse(
        id=s.id,
        tenant_id=s.tenant_id,
        nome=s.nome,
        categoria=s.categoria,
        duracao_minutos=s.duracao_minutos,
        ativo=s.ativo,
        precos=[
            PrecoResponse(
                id=p.id,
                servico_id=p.servico_id,
                qtd_min=p.qtd_min,
                qtd_max=p.qtd_max,
                preco_particular=float(p.preco_particular),
                preco_convenio=float(p.preco_convenio) if p.preco_convenio is not None else None,
                convenio=p.convenio
            ) for p in created_prices
        ]
    )

@router.put("/servicos/{id}", response_model=ServicoProdutoResponse)
async def update_servico(
    id: uuid.UUID,
    servico_data: ServicoProdutoCreate,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    s = await db.get(ServicoProduto, id)
    if not s:
        raise HTTPException(status_code=404, detail="Serviço/Produto não encontrado.")
        
    s.nome = servico_data.nome
    s.categoria = servico_data.categoria
    s.duracao_minutos = servico_data.duracao_minutos
    s.ativo = servico_data.ativo

    # Delete existing prices and recreate if provided
    await db.execute(delete(Preco).where(Preco.servico_id == s.id))
    
    created_prices = []
    if servico_data.precos:
        for p_data in servico_data.precos:
            p = Preco(
                id=uuid.uuid4(),
                tenant_id=current_user.tenant_id,
                servico_id=s.id,
                qtd_min=p_data.qtd_min,
                qtd_max=p_data.qtd_max,
                preco_particular=p_data.preco_particular,
                preco_convenio=p_data.preco_convenio,
                convenio=p_data.convenio
            )
            db.add(p)
            created_prices.append(p)
            
    await db.commit()
    
    return ServicoProdutoResponse(
        id=s.id,
        tenant_id=s.tenant_id,
        nome=s.nome,
        categoria=s.categoria,
        duracao_minutos=s.duracao_minutos,
        ativo=s.ativo,
        precos=[
            PrecoResponse(
                id=p.id,
                servico_id=p.servico_id,
                qtd_min=p.qtd_min,
                qtd_max=p.qtd_max,
                preco_particular=float(p.preco_particular),
                preco_convenio=float(p.preco_convenio) if p.preco_convenio is not None else None,
                convenio=p.convenio
            ) for p in created_prices
        ]
    )

@router.get("/lista-espera", response_model=List[ListaEsperaResponse])
async def list_lista_espera(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    stmt = select(
        ListaEspera, 
        ClientePaciente.nome, 
        ClientePaciente.whatsapp,
        ServicoProduto.nome
    ).join(
        ClientePaciente, ListaEspera.cliente_id == ClientePaciente.id
    ).outerjoin(
        ServicoProduto, ListaEspera.servico_id == ServicoProduto.id
    ).where(
        ListaEspera.status == "aguardando"
    ).order_by(ListaEspera.data_preferida.asc())

    results = (await db.execute(stmt)).all()
    
    return [
        ListaEsperaResponse(
            id=row[0].id,
            tenant_id=row[0].tenant_id,
            cliente_id=row[0].cliente_id,
            servico_id=row[0].servico_id,
            data_preferida=row[0].data_preferida,
            status=row[0].status,
            cliente_nome=row[1],
            cliente_whatsapp=row[2],
            servico_nome=row[3]
        )
        for row in results
    ]

@router.post("/lista-espera", response_model=ListaEsperaResponse, status_code=201)
async def add_lista_espera(
    payload: ListaEsperaCreate,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    # Verify client exists
    client = await db.get(ClientePaciente, payload.cliente_id)
    if not client:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")

    if payload.servico_id and not await db.get(ServicoProduto, payload.servico_id):
        raise HTTPException(status_code=404, detail="Serviço/Produto não encontrado.")

    entry = ListaEspera(
        id=uuid.uuid4(),
        tenant_id=current_user.tenant_id,
        cliente_id=payload.cliente_id,
        servico_id=payload.servico_id,
        data_preferida=payload.data_preferida,
        status="aguardando"
    )
    db.add(entry)
    await db.commit()
    
    servico_nome = None
    if payload.servico_id:
        serv = await db.get(ServicoProduto, payload.servico_id)
        servico_nome = serv.nome if serv else None

    return ListaEsperaResponse(
        id=entry.id,
        tenant_id=entry.tenant_id,
        cliente_id=entry.cliente_id,
        servico_id=entry.servico_id,
        data_preferida=entry.data_preferida,
        status=entry.status,
        cliente_nome=client.nome,
        cliente_whatsapp=client.whatsapp,
        servico_nome=servico_nome
    )

@router.post("/lista-espera/{id}/oferecer")
async def oferecer_horario_espera(
    id: uuid.UUID,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    from app.services.lista_espera_service import oferecer_vaga_lista_espera
    
    entry = await db.get(ListaEspera, id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entrada de lista de espera não encontrada.")

    # Call the existing service to dispatch offer WhatsApp message
    success = await oferecer_vaga_lista_espera(db, entry)
    if success:
        await db.commit()
        return {"status": "success", "message": "Oferta enviada via WhatsApp."}
    else:
        raise HTTPException(status_code=500, detail="Erro ao enviar mensagem de oferta.")

@router.delete("/lista-espera/{id}", status_code=204)
async def delete_lista_espera(
    id: uuid.UUID,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    entry = await db.get(ListaEspera, id)
    if not entry:
        raise HTTPException(status_code=404, detail="Entrada não encontrada.")
    await db.delete(entry)
    await db.commit()
    return None


@router.get("/usuarios", response_model=List[OperatorResponse])
async def list_usuarios(
    current_user: Usuario = Depends(require_roles("dono")),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Usuario)
        .where(Usuario.tenant_id == current_user.tenant_id, Usuario.ativo.is_(True))
        .order_by(Usuario.nome.asc())
    )
    return result.scalars().all()


@router.post("/usuarios", response_model=OperatorResponse, status_code=201)
async def create_usuario(
    payload: OperatorCreate,
    current_user: Usuario = Depends(require_roles("dono")),
    db: AsyncSession = Depends(get_db),
):
    try:
        validate_password_strength(payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    existing = (await db.execute(
        select(Usuario.id).where(func.lower(Usuario.email) == str(payload.email).lower())
    )).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="E-mail já cadastrado.")

    operator = Usuario(
        id=uuid.uuid4(),
        tenant_id=current_user.tenant_id,
        nome=payload.nome,
        email=str(payload.email).lower(),
        senha_hash=get_password_hash(payload.password),
        perfil=payload.perfil,
        ativo=True,
    )
    db.add(operator)
    db.add(LogAuditoria(
        id=uuid.uuid4(),
        tenant_id=current_user.tenant_id,
        usuario_id=current_user.id,
        usuario_email=current_user.email,
        acao="USER_CREATE",
        tabela="usuarios",
        registro_id=operator.id,
        valores_novos=json.dumps({"email": operator.email, "perfil": operator.perfil}),
    ))
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=400, detail="E-mail já cadastrado.") from exc
    await db.refresh(operator)
    return operator


@router.delete("/usuarios/{id}", status_code=204)
async def deactivate_usuario(
    id: uuid.UUID,
    current_user: Usuario = Depends(require_roles("dono")),
    db: AsyncSession = Depends(get_db),
):
    operator = await db.get(Usuario, id)
    if not operator or not operator.ativo:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    if operator.id == current_user.id or operator.perfil == "dono":
        raise HTTPException(status_code=400, detail="O usuário proprietário não pode ser desativado.")

    operator.ativo = False
    operator.token_version += 1
    db.add(LogAuditoria(
        id=uuid.uuid4(),
        tenant_id=current_user.tenant_id,
        usuario_id=current_user.id,
        usuario_email=current_user.email,
        acao="USER_DEACTIVATE",
        tabela="usuarios",
        registro_id=operator.id,
        valores_antigos=json.dumps({"email": operator.email, "perfil": operator.perfil, "ativo": True}),
        valores_novos=json.dumps({"ativo": False}),
    ))
    await db.commit()
    return None

@router.get("/configuracoes", response_model=ConfiguracaoResponse)
async def get_configuracoes(
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    config = (await db.execute(
        select(Configuracao).where(Configuracao.tenant_id == current_user.tenant_id)
    )).scalar_one_or_none()
    
    if not config:
        # Create a default configuration entry if missing
        config = Configuracao(
            id=uuid.uuid4(),
            tenant_id=current_user.tenant_id,
            limite_pedido_grande=10,
            mensagem_boas_vindas="Olá! Seja bem-vindo.",
            mensagem_fora_horario="Estamos fora do expediente.",
            mensagem_confirmacao="Confirma sua presença?",
            mensagem_reativacao="Olá! Sumiu por que?"
        )
        db.add(config)
        await db.commit()
        await db.refresh(config)
        
    tenant = await db.get(Tenant, current_user.tenant_id)
    config.sistema_ativo = tenant.sistema_ativo if tenant else True
    config.owner_whatsapp = tenant.owner_whatsapp if tenant else None
    config.evolution_instance_name = tenant.evolution_instance_name if tenant else None
    config.tenant_nome = tenant.nome if tenant else None
    config.tenant_tipo = tenant.tipo if tenant else None
    config.tenant_cor_primaria = tenant.cor_primaria if tenant else None
    config.tenant_logo_url = tenant.logo_url if tenant else None
    return config


@router.put("/configuracoes", response_model=ConfiguracaoResponse)
async def update_configuracoes(
    payload: ConfiguracaoUpdate,
    current_user: Usuario = Depends(require_roles("dono")),
    db: AsyncSession = Depends(get_db)
):
    config = (await db.execute(
        select(Configuracao).where(Configuracao.tenant_id == current_user.tenant_id)
    )).scalar_one_or_none()
    
    if not config:
        config = Configuracao(
            id=uuid.uuid4(),
            tenant_id=current_user.tenant_id,
            limite_pedido_grande=payload.limite_pedido_grande or 10,
            mensagem_boas_vindas=payload.mensagem_boas_vindas,
            mensagem_fora_horario=payload.mensagem_fora_horario,
            mensagem_confirmacao=payload.mensagem_confirmacao,
            mensagem_reativacao=payload.mensagem_reativacao,
            horario_funcionamento=payload.horario_funcionamento
        )
        db.add(config)
    else:
        if payload.limite_pedido_grande is not None:
            config.limite_pedido_grande = payload.limite_pedido_grande
        if payload.mensagem_boas_vindas is not None:
            config.mensagem_boas_vindas = payload.mensagem_boas_vindas
        if payload.mensagem_fora_horario is not None:
            config.mensagem_fora_horario = payload.mensagem_fora_horario
        if payload.mensagem_confirmacao is not None:
            config.mensagem_confirmacao = payload.mensagem_confirmacao
        if payload.mensagem_reativacao is not None:
            config.mensagem_reativacao = payload.mensagem_reativacao
        if payload.horario_funcionamento is not None:
            config.horario_funcionamento = payload.horario_funcionamento
            
    # Also update Tenant fields for quick access if needed
    tenant = await db.get(Tenant, current_user.tenant_id)
    if tenant:
        if payload.limite_pedido_grande is not None:
            tenant.limite_pedido_grande = payload.limite_pedido_grande
        if payload.sistema_ativo is not None:
            if current_user.perfil != "dono":
                raise HTTPException(
                    status_code=403,
                    detail="Apenas o proprietário (dono) pode alterar o estado do sistema (Kill Switch)."
            )
            tenant.sistema_ativo = payload.sistema_ativo
        if "owner_whatsapp" in payload.model_fields_set:
            tenant.owner_whatsapp = payload.owner_whatsapp.strip() if payload.owner_whatsapp else None
        if "evolution_instance_name" in payload.model_fields_set:
            tenant.evolution_instance_name = payload.evolution_instance_name.strip() if payload.evolution_instance_name else None
        db.add(tenant)
        
    await db.commit()
    await db.refresh(config)
    config.sistema_ativo = tenant.sistema_ativo if tenant else True
    config.owner_whatsapp = tenant.owner_whatsapp if tenant else None
    config.evolution_instance_name = tenant.evolution_instance_name if tenant else None
    config.tenant_nome = tenant.nome if tenant else None
    config.tenant_tipo = tenant.tipo if tenant else None
    config.tenant_cor_primaria = tenant.cor_primaria if tenant else None
    config.tenant_logo_url = tenant.logo_url if tenant else None
    return config


@router.get("/relatorios/pdf/dia")
async def download_pdf_dia(
    data: Optional[date] = None,
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    tenant = await db.get(Tenant, current_user.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado.")

    data_rel = data or date.today()
    start_dt = datetime.combine(data_rel, time.min).replace(tzinfo=ZoneInfo("America/Sao_Paulo"))
    end_dt = datetime.combine(data_rel, time.max).replace(tzinfo=ZoneInfo("America/Sao_Paulo"))

    # 1. Fetch unique appointments and client names (1-to-1 client-appointment relationship)
    appts_query = (
        select(AtendimentoPedido, ClientePaciente.nome)
        .join(ClientePaciente, AtendimentoPedido.cliente_id == ClientePaciente.id)
        .where(
            AtendimentoPedido.data_agendamento >= start_dt,
            AtendimentoPedido.data_agendamento <= end_dt
        )
        .order_by(AtendimentoPedido.data_agendamento.asc())
    )
    appts_rows = (await db.execute(appts_query)).all()

    # 2. Batch query all items for these appointments to find associated service names
    appt_ids = [row[0].id for row in appts_rows]
    items_by_appt = {}
    if appt_ids:
        items_query = (
            select(ItemAtendimento.atendimento_id, ServicoProduto.nome)
            .join(ServicoProduto, ItemAtendimento.servico_id == ServicoProduto.id)
            .where(ItemAtendimento.atendimento_id.in_(appt_ids))
        )
        items_rows = (await db.execute(items_query)).all()
        for appt_id, service_name in items_rows:
            if appt_id not in items_by_appt:
                items_by_appt[appt_id] = []
            items_by_appt[appt_id].append(service_name)

    total_atendimentos = len(appts_rows)
    realizados = sum(1 for r in appts_rows if r[0].status in ["realizado", "entregue"])
    faltas = sum(1 for r in appts_rows if r[0].status == "falta")
    cancelados = sum(1 for r in appts_rows if r[0].status == "cancelado")
    em_producao = sum(1 for r in appts_rows if r[0].status == "em_producao")
    receita_total = sum(float(r[0].total) for r in appts_rows)
    receita_recebida = sum(float(r[0].total) for r in appts_rows if r[0].pago)
    receita_pendente = receita_total - receita_recebida

    # Fetch night messages count
    mensagens_noturnas = (await db.execute(
        select(func.count(LogMensagem.id)).where(
            LogMensagem.criado_em >= start_dt,
            LogMensagem.criado_em <= end_dt,
            LogMensagem.direcao == "entrada"
        )
    )).scalar() or 0

    dados_dia = {
        "total_atendimentos": total_atendimentos,
        "realizados": realizados,
        "faltas": faltas,
        "cancelados": cancelados,
        "em_producao": em_producao,
        "receita_total": receita_total,
        "receita_recebida": receita_recebida,
        "receita_pendente": receita_pendente,
        "mensagens_noturnas": mensagens_noturnas,
        "atendimentos": [
            {
                "horario": r[0].data_agendamento.astimezone(ZoneInfo("America/Sao_Paulo")).strftime("%H:%M") if r[0].data_agendamento.tzinfo else r[0].data_agendamento.strftime("%H:%M"),
                "cliente": r[1],
                "servico": ", ".join(items_by_appt.get(r[0].id, [])) or "Serviço",
                "status": r[0].status
            }
            for r in appts_rows
        ]
    }

    pdf_bytes = gerar_pdf_fechamento_diario(
        tenant_nome=tenant.nome,
        cor_primaria=tenant.cor_primaria,
        data_relatorio=data_rel,
        dados=dados_dia
    )

    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=fechamento_{data_rel.isoformat()}.pdf"}
    )

@router.get("/relatorios/pdf/mensal")
async def download_pdf_mensal(
    mes_ano: Optional[str] = Query(None, pattern=r"^(0[1-9]|1[0-2])/\d{4}$", description="Formato MM/AAAA"),
    current_user: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    tenant = await db.get(Tenant, current_user.tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant não encontrado.")

    now_sp = datetime.now(ZoneInfo("America/Sao_Paulo"))
    mes_ano_str = mes_ano or now_sp.strftime("%m/%Y")
    month, year = (int(part) for part in mes_ano_str.split("/"))
    start_dt = datetime(year, month, 1, tzinfo=ZoneInfo("America/Sao_Paulo"))
    if month == 12:
        end_dt = datetime(year + 1, 1, 1, tzinfo=ZoneInfo("America/Sao_Paulo"))
    else:
        end_dt = datetime(year, month + 1, 1, tzinfo=ZoneInfo("America/Sao_Paulo"))
    in_month = (
        AtendimentoPedido.data_agendamento >= start_dt,
        AtendimentoPedido.data_agendamento < end_dt,
    )
    
    # Calculate stats
    realizados_count = (await db.execute(
        select(func.count(AtendimentoPedido.id)).where(*in_month, AtendimentoPedido.status.in_(["realizado", "entregue"]))
    )).scalar() or 0
    
    receita_total = float((await db.execute(
        select(func.sum(AtendimentoPedido.total)).where(*in_month, AtendimentoPedido.status.in_(["realizado", "entregue"]))
    )).scalar() or 0.0)

    faltas_count = (await db.execute(
        select(func.count(AtendimentoPedido.id)).where(*in_month, AtendimentoPedido.status == "falta")
    )).scalar() or 0
    
    total_comp_denom = realizados_count + faltas_count
    taxa_comparecimento = (realizados_count / total_comp_denom * 100) if total_comp_denom > 0 else 100.0

    receita_perdida_faltas = float((await db.execute(
        select(func.sum(AtendimentoPedido.total)).where(*in_month, AtendimentoPedido.status == "falta")
    )).scalar() or 0.0)

    reativados_crm = (await db.execute(
        select(func.count(ClientePaciente.id)).where(
            ClientePaciente.status_reativacao == "reativado",
            ClientePaciente.reativado_em >= start_dt,
            ClientePaciente.reativado_em < end_dt,
        )
    )).scalar() or 0

    consultas_lista_espera = (await db.execute(
        select(func.count(ListaEspera.id)).where(
            ListaEspera.status == "agendado",
            ListaEspera.agendado_em >= start_dt,
            ListaEspera.agendado_em < end_dt,
        )
    )).scalar() or 0

    ticket_avg = float((await db.execute(
        select(func.avg(AtendimentoPedido.total)).where(*in_month, AtendimentoPedido.status.in_(["realizado", "entregue"]))
    )).scalar() or 150.0)

    impacto_total = (reativados_crm * ticket_avg) + (consultas_lista_espera * ticket_avg)

    mensalidade_map = {"starter": 99.0, "pro": 199.0, "premium": 399.0}
    mensalidade = mensalidade_map.get(tenant.plano, 199.0)
    roi = (impacto_total / mensalidade) if mensalidade > 0 else 0.0

    dados_roi = {
        "total_atendimentos": realizados_count,
        "taxa_comparecimento": taxa_comparecimento,
        "receita_total": receita_total,
        "receita_perdida_faltas": receita_perdida_faltas,
        "reativados_crm": reativados_crm,
        "consultas_lista_espera": consultas_lista_espera,
        "impacto_total": impacto_total,
        "mensalidade": mensalidade,
        "roi": roi
    }

    pdf_bytes = gerar_pdf_roi_mensal(
        tenant_nome=tenant.nome,
        cor_primaria=tenant.cor_primaria,
        mes_ano=mes_ano_str,
        dados=dados_roi
    )

    clean_filename = mes_ano_str.replace("/", "_")
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=roi_{clean_filename}.pdf"}
    )
