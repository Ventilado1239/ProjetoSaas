import uuid
import json
from datetime import date, datetime, timezone
from typing import Literal, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.models.models import (
    AtendimentoPedido,
    ClientePaciente,
    Configuracao,
    MasterAdmin,
    MasterAuditLog,
    MasterLead,
    ServicoProduto,
    Tenant,
    Usuario,
)
from app.utils.security import DUMMY_PASSWORD_HASH, create_access_token, decode_token, get_password_hash, validate_password_strength, verify_password
from app.services import asaas_service

router = APIRouter(prefix="/master", tags=["master"])


class MasterLoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=72)


class MasterTenantCreate(BaseModel):
    nome: str = Field(min_length=2, max_length=255)
    tipo: Literal["clinica", "loja"] = "clinica"
    whatsapp_numero: str = Field(min_length=10, max_length=50)
    owner_whatsapp: Optional[str] = Field(default=None, max_length=50)
    evolution_instance_name: Optional[str] = Field(default=None, min_length=3, max_length=120, pattern=r"^[A-Za-z0-9_-]+$")
    responsavel_nome: Optional[str] = Field(default=None, max_length=255)
    responsavel_email: Optional[EmailStr] = None
    admin_nome: str = Field(default="Administrador", min_length=2, max_length=255)
    admin_email: EmailStr
    admin_password: str = Field(min_length=12, max_length=72)
    plano: Literal["starter", "pro", "premium"] = "starter"
    mensalidade: Optional[float] = Field(default=None, ge=0, le=99999999.99)
    cor_primaria: str = Field(default="#2563eb", pattern=r"^#[0-9A-Fa-f]{6}$")
    proximo_vencimento: Optional[date] = None
    observacoes: Optional[str] = Field(default=None, max_length=2048)

    @field_validator("admin_password")
    @classmethod
    def strong_admin_password(cls, value: str) -> str:
        validate_password_strength(value)
        return value

    @field_validator("evolution_instance_name", mode="before")
    @classmethod
    def empty_instance_as_none(cls, value):
        return value or None


class MasterTenantUpdate(BaseModel):
    nome: Optional[str] = None
    plano: Optional[Literal["starter", "pro", "premium"]] = None
    sistema_ativo: Optional[bool] = None
    pagamento_status: Optional[Literal["em_dia", "atrasado", "inadimplente", "cancelado"]] = None
    crm_stage: Optional[Literal["lead", "demo", "proposta", "negociacao", "onboarding", "ativo", "risco", "inativo", "cancelado"]] = None
    mensalidade: Optional[float] = Field(default=None, ge=0, le=99999999.99)
    proximo_vencimento: Optional[date] = None
    responsavel_nome: Optional[str] = None
    responsavel_email: Optional[EmailStr] = None
    owner_whatsapp: Optional[str] = None
    evolution_instance_name: Optional[str] = None
    observacoes: Optional[str] = None


class ResetPasswordRequest(BaseModel):
    email: Optional[EmailStr] = None
    new_password: str = Field(min_length=12, max_length=72)

    @field_validator("new_password")
    @classmethod
    def strong_new_password(cls, value: str) -> str:
        validate_password_strength(value)
        return value


class BillingSubscriptionRequest(BaseModel):
    cpf_cnpj: str = Field(min_length=11, max_length=18)
    next_due_date: date
    billing_type: Literal["PIX", "BOLETO", "CREDIT_CARD", "UNDEFINED"] = "PIX"
    cycle: Literal["WEEKLY", "BIWEEKLY", "MONTHLY", "QUARTERLY", "SEMIANNUALLY", "YEARLY"] = "MONTHLY"
    description: Optional[str] = Field(default=None, max_length=255)

    @field_validator("cpf_cnpj")
    @classmethod
    def valid_cpf_cnpj(cls, value: str) -> str:
        digits = "".join(ch for ch in value if ch.isdigit())
        if len(digits) not in {11, 14}:
            raise ValueError("CPF/CNPJ deve conter 11 ou 14 digitos.")
        return digits


class LeadCreate(BaseModel):
    nome_clinica: str
    responsavel_nome: Optional[str] = None
    responsavel_email: Optional[EmailStr] = None
    whatsapp: Optional[str] = None
    etapa: Literal["lead", "demo", "proposta", "negociacao", "ganho", "perdido"] = "lead"
    valor_potencial: Optional[float] = Field(default=None, ge=0, le=99999999.99)
    proxima_acao: Optional[str] = None
    observacoes: Optional[str] = None


class LeadUpdate(BaseModel):
    nome_clinica: Optional[str] = None
    responsavel_nome: Optional[str] = None
    responsavel_email: Optional[EmailStr] = None
    whatsapp: Optional[str] = None
    etapa: Optional[Literal["lead", "demo", "proposta", "negociacao", "ganho", "perdido"]] = None
    valor_potencial: Optional[float] = Field(default=None, ge=0, le=99999999.99)
    proxima_acao: Optional[str] = None
    observacoes: Optional[str] = None


def normalize_phone(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    digits = "".join(ch for ch in value if ch.isdigit())
    return digits or None


def add_master_audit(
    db: AsyncSession,
    admin: MasterAdmin,
    request: Request,
    action: str,
    entity: str,
    entity_id: Optional[uuid.UUID] = None,
    details: Optional[dict] = None,
) -> None:
    db.add(MasterAuditLog(
        id=uuid.uuid4(),
        admin_id=admin.id,
        acao=action,
        entidade=entity,
        entidade_id=entity_id,
        detalhes=json.dumps(details, ensure_ascii=False, default=str)[:2048] if details else None,
        ip_origem=request.client.host[:64] if request.client else None,
    ))


async def get_current_master(request: Request, db: AsyncSession = Depends(get_db)) -> MasterAdmin:
    token = request.cookies.get("master_access_token")
    if not token:
        raise HTTPException(status_code=401, detail="Master não autenticado.")

    payload = decode_token(token)
    if not payload or payload.get("type") != "access" or payload.get("scope") != "master":
        raise HTTPException(status_code=401, detail="Token master inválido.")

    admin_id = payload.get("sub")
    try:
        admin_uuid = uuid.UUID(admin_id)
    except (TypeError, ValueError):
        raise HTTPException(status_code=401, detail="Token master inválido.")

    await db.execute(text("SET LOCAL app.bypass_rls = 'true'"))
    admin = await db.get(MasterAdmin, admin_uuid)
    if not admin or not admin.ativo:
        raise HTTPException(status_code=401, detail="Master não encontrado ou inativo.")
    return admin


@router.post("/auth/login")
async def master_login(payload: MasterLoginRequest, request: Request, response: Response, db: AsyncSession = Depends(get_db)):
    await db.execute(text("SET LOCAL app.bypass_rls = 'true'"))
    admin = (await db.execute(
        select(MasterAdmin).where(func.lower(MasterAdmin.email) == str(payload.email).strip().lower())
    )).scalar_one_or_none()

    password_valid = verify_password(payload.password, admin.senha_hash if admin else DUMMY_PASSWORD_HASH)
    if not admin or not admin.ativo or not password_valid:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Credenciais master inválidas.")

    token = create_access_token({"sub": str(admin.id), "scope": "master", "perfil": "master"})
    admin.ultimo_login_em = datetime.now(timezone.utc)
    add_master_audit(db, admin, request, "LOGIN", "master_admin", admin.id)
    await db.commit()
    response.set_cookie(
        key="master_access_token",
        value=token,
        httponly=True,
        secure=settings.ENVIRONMENT == "production",
        samesite="strict",
        max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        path="/master",
    )
    return {"message": "Login master realizado", "user": {"id": admin.id, "nome": admin.nome, "email": admin.email, "perfil": "master"}}


@router.post("/auth/logout")
async def master_logout(response: Response):
    response.delete_cookie(key="master_access_token", path="/master")
    return {"message": "Logout master realizado"}


@router.get("/me")
async def master_me(admin: MasterAdmin = Depends(get_current_master)):
    return {"id": admin.id, "nome": admin.nome, "email": admin.email, "perfil": "master"}


@router.get("/summary")
async def master_summary(admin: MasterAdmin = Depends(get_current_master), db: AsyncSession = Depends(get_db)):
    await db.execute(text("SET LOCAL app.bypass_rls = 'true'"))
    tenants = (await db.execute(select(Tenant))).scalars().all()
    leads_count = (await db.execute(select(func.count(MasterLead.id)))).scalar() or 0
    mrr = sum(float(t.mensalidade or 0) for t in tenants if t.crm_stage == "ativo" and t.sistema_ativo)
    inadimplentes = sum(1 for t in tenants if t.pagamento_status in {"atrasado", "inadimplente"})
    return {
        "clientes_total": len(tenants),
        "clientes_ativos": sum(1 for t in tenants if t.sistema_ativo),
        "inadimplentes": inadimplentes,
        "leads_total": leads_count,
        "mrr": mrr,
    }


@router.get("/tenants")
async def list_master_tenants(admin: MasterAdmin = Depends(get_current_master), db: AsyncSession = Depends(get_db)):
    await db.execute(text("SET LOCAL app.bypass_rls = 'true'"))
    rows = (await db.execute(select(Tenant).order_by(Tenant.nome.asc()))).scalars().all()
    result = []
    for tenant in rows:
        await db.execute(text("SELECT set_tenant_id(:tenant_id)"), {"tenant_id": tenant.id})
        pacientes = (await db.execute(select(func.count(ClientePaciente.id)).where(ClientePaciente.tenant_id == tenant.id))).scalar() or 0
        usuarios = (await db.execute(select(func.count(Usuario.id)).where(Usuario.tenant_id == tenant.id))).scalar() or 0
        atendimentos = (await db.execute(select(func.count(AtendimentoPedido.id)).where(AtendimentoPedido.tenant_id == tenant.id))).scalar() or 0
        result.append({
            "id": tenant.id,
            "nome": tenant.nome,
            "tipo": tenant.tipo,
            "plano": tenant.plano,
            "sistema_ativo": tenant.sistema_ativo,
            "pagamento_status": tenant.pagamento_status,
            "crm_stage": tenant.crm_stage,
            "mensalidade": float(tenant.mensalidade or 0),
            "proximo_vencimento": tenant.proximo_vencimento,
            "responsavel_nome": tenant.responsavel_nome,
            "responsavel_email": tenant.responsavel_email,
            "whatsapp_numero": tenant.whatsapp_numero,
            "owner_whatsapp": tenant.owner_whatsapp,
            "evolution_instance_name": tenant.evolution_instance_name,
            "asaas_customer_id": tenant.asaas_customer_id,
            "asaas_subscription_id": tenant.asaas_subscription_id,
            "pacientes": pacientes,
            "usuarios": usuarios,
            "atendimentos": atendimentos,
        })
    await db.execute(text("SET LOCAL app.bypass_rls = 'true'"))
    return result


@router.post("/tenants", status_code=201)
async def create_master_tenant(payload: MasterTenantCreate, request: Request, admin: MasterAdmin = Depends(get_current_master), db: AsyncSession = Depends(get_db)):
    await db.execute(text("SET LOCAL app.bypass_rls = 'true'"))
    normalized_admin_email = str(payload.admin_email).strip().lower()
    existing_user = (await db.execute(
        select(Usuario).where(func.lower(Usuario.email) == normalized_admin_email)
    )).scalar_one_or_none()
    if existing_user:
        raise HTTPException(status_code=400, detail="Já existe usuário com este e-mail.")

    tenant_id = uuid.uuid4()
    instance_name = payload.evolution_instance_name or f"saas_tenant_{tenant_id}"
    tenant = Tenant(
        id=tenant_id,
        nome=payload.nome,
        tipo=payload.tipo,
        whatsapp_numero=normalize_phone(payload.whatsapp_numero) or payload.whatsapp_numero,
        owner_whatsapp=normalize_phone(payload.owner_whatsapp) or normalize_phone(payload.whatsapp_numero),
        evolution_instance_name=instance_name,
        plano=payload.plano,
        sistema_ativo=True,
        cor_primaria=payload.cor_primaria,
        responsavel_nome=payload.responsavel_nome or payload.admin_nome,
        responsavel_email=str(payload.responsavel_email or payload.admin_email),
        mensalidade=payload.mensalidade,
        pagamento_status="em_dia",
        crm_stage="ativo",
        proximo_vencimento=payload.proximo_vencimento,
        observacoes=payload.observacoes,
    )
    db.add(tenant)
    await db.flush()
    await db.execute(text("SELECT set_tenant_id(:tenant_id)"), {"tenant_id": tenant_id})

    db.add(Usuario(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        nome=payload.admin_nome,
        email=normalized_admin_email,
        senha_hash=get_password_hash(payload.admin_password),
        perfil="dono",
    ))
    db.add(Configuracao(id=uuid.uuid4(), tenant_id=tenant_id, limite_pedido_grande=10))
    for name, duration in [("Consulta", 60), ("Retorno", 30), ("Avaliação", 45)]:
        db.add(ServicoProduto(id=uuid.uuid4(), tenant_id=tenant_id, nome=name, categoria="Atendimento", duracao_minutos=duration, ativo=True))

    add_master_audit(db, admin, request, "CREATE", "tenant", tenant_id, {"nome": payload.nome, "admin_email": normalized_admin_email})

    await db.commit()
    return {"id": tenant_id, "admin_email": payload.admin_email, "evolution_instance_name": instance_name}


@router.put("/tenants/{tenant_id}")
async def update_master_tenant(tenant_id: uuid.UUID, payload: MasterTenantUpdate, request: Request, admin: MasterAdmin = Depends(get_current_master), db: AsyncSession = Depends(get_db)):
    await db.execute(text("SET LOCAL app.bypass_rls = 'true'"))
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Cliente não encontrado.")

    for field, value in payload.model_dump(exclude_unset=True).items():
        if field in {"owner_whatsapp"} and value is not None:
            value = normalize_phone(value)
        setattr(tenant, field, value)
    add_master_audit(db, admin, request, "UPDATE", "tenant", tenant_id, {"campos": sorted(payload.model_fields_set)})
    await db.commit()
    return {"status": "updated"}


@router.post("/tenants/{tenant_id}/reset-password")
async def reset_tenant_password(tenant_id: uuid.UUID, payload: ResetPasswordRequest, request: Request, admin: MasterAdmin = Depends(get_current_master), db: AsyncSession = Depends(get_db)):
    await db.execute(text("SET LOCAL app.bypass_rls = 'true'"))
    stmt = select(Usuario).where(Usuario.tenant_id == tenant_id)
    if payload.email:
        stmt = stmt.where(func.lower(Usuario.email) == str(payload.email).strip().lower())
    else:
        stmt = stmt.where(Usuario.perfil == "dono")
    user = (await db.execute(stmt.order_by(Usuario.email.asc()))).scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuário da clínica não encontrado.")
    user.senha_hash = get_password_hash(payload.new_password)
    user.token_version += 1
    add_master_audit(db, admin, request, "RESET_PASSWORD", "usuario", user.id, {"email": user.email, "tenant_id": tenant_id})
    await db.commit()
    return {"status": "password_reset", "email": user.email}


@router.post("/tenants/{tenant_id}/billing/subscription", status_code=201)
async def create_tenant_billing_subscription(
    tenant_id: uuid.UUID,
    payload: BillingSubscriptionRequest,
    request: Request,
    admin: MasterAdmin = Depends(get_current_master),
    db: AsyncSession = Depends(get_db),
):
    """Creates the tenant's recurring Asaas subscription without persisting CPF/CNPJ."""
    await db.execute(text("SET LOCAL app.bypass_rls = 'true'"))
    tenant = await db.get(Tenant, tenant_id)
    if not tenant:
        raise HTTPException(status_code=404, detail="Cliente nao encontrado.")
    if tenant.asaas_subscription_id:
        raise HTTPException(status_code=409, detail="Cliente ja possui assinatura Asaas.")
    if not tenant.mensalidade or float(tenant.mensalidade) <= 0:
        raise HTTPException(status_code=422, detail="Defina uma mensalidade positiva antes de criar a assinatura.")

    try:
        if not tenant.asaas_customer_id:
            customer = await asaas_service.create_customer(
                tenant_id=str(tenant.id),
                name=tenant.responsavel_nome or tenant.nome,
                cpf_cnpj=payload.cpf_cnpj,
                email=tenant.responsavel_email,
                mobile_phone=tenant.owner_whatsapp or tenant.whatsapp_numero,
            )
            tenant.asaas_customer_id = str(customer["id"])[:64]
            add_master_audit(db, admin, request, "ASAAS_CUSTOMER_CREATE", "tenant", tenant.id)
            await db.commit()
            await db.execute(text("SET LOCAL app.bypass_rls = 'true'"))

        subscription = await asaas_service.create_subscription(
            tenant_id=str(tenant.id),
            customer_id=tenant.asaas_customer_id,
            value=float(tenant.mensalidade),
            next_due_date=payload.next_due_date.isoformat(),
            billing_type=payload.billing_type,
            cycle=payload.cycle,
            description=payload.description or f"Plano {tenant.plano} - {tenant.nome}",
        )
    except asaas_service.AsaasAPIError as exc:
        await db.rollback()
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    tenant.asaas_subscription_id = str(subscription["id"])[:64]
    tenant.proximo_vencimento = payload.next_due_date
    tenant.pagamento_status = "em_dia"
    add_master_audit(db, admin, request, "ASAAS_SUBSCRIPTION_CREATE", "tenant", tenant.id, {
        "billing_type": payload.billing_type,
        "cycle": payload.cycle,
        "next_due_date": payload.next_due_date,
    })
    await db.commit()
    return {
        "status": "created",
        "customer_id": tenant.asaas_customer_id,
        "subscription_id": tenant.asaas_subscription_id,
        "next_due_date": tenant.proximo_vencimento,
    }


@router.get("/leads")
async def list_leads(admin: MasterAdmin = Depends(get_current_master), db: AsyncSession = Depends(get_db)):
    await db.execute(text("SET LOCAL app.bypass_rls = 'true'"))
    leads = (await db.execute(select(MasterLead).order_by(MasterLead.atualizado_em.desc()))).scalars().all()
    return [
        {
            "id": lead.id,
            "nome_clinica": lead.nome_clinica,
            "responsavel_nome": lead.responsavel_nome,
            "responsavel_email": lead.responsavel_email,
            "whatsapp": lead.whatsapp,
            "etapa": lead.etapa,
            "valor_potencial": float(lead.valor_potencial or 0),
            "proxima_acao": lead.proxima_acao,
            "observacoes": lead.observacoes,
            "criado_em": lead.criado_em,
            "atualizado_em": lead.atualizado_em,
        }
        for lead in leads
    ]


@router.post("/leads", status_code=201)
async def create_lead(payload: LeadCreate, request: Request, admin: MasterAdmin = Depends(get_current_master), db: AsyncSession = Depends(get_db)):
    await db.execute(text("SET LOCAL app.bypass_rls = 'true'"))
    lead = MasterLead(id=uuid.uuid4(), **payload.model_dump())
    db.add(lead)
    add_master_audit(db, admin, request, "CREATE", "lead", lead.id, {"nome_clinica": lead.nome_clinica})
    await db.commit()
    return {"id": lead.id}


@router.put("/leads/{lead_id}")
async def update_lead(lead_id: uuid.UUID, payload: LeadUpdate, request: Request, admin: MasterAdmin = Depends(get_current_master), db: AsyncSession = Depends(get_db)):
    await db.execute(text("SET LOCAL app.bypass_rls = 'true'"))
    lead = await db.get(MasterLead, lead_id)
    if not lead:
        raise HTTPException(status_code=404, detail="Lead não encontrado.")
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(lead, field, value)
    add_master_audit(db, admin, request, "UPDATE", "lead", lead_id, {"campos": sorted(payload.model_fields_set)})
    await db.commit()
    return {"status": "updated"}
