import argparse
import asyncio
import uuid

from sqlalchemy import select, text

from app.database import AsyncSessionLocal
from app.models.models import Configuracao, ServicoProduto, Tenant, Usuario
from app.utils.security import get_password_hash, validate_password_strength


DEFAULT_CLINIC_SERVICES = [
    ("Consulta", "Atendimento", 60),
    ("Retorno", "Atendimento", 30),
    ("Avaliação", "Atendimento", 45),
]


def normalize_phone(value: str) -> str:
    digits = "".join(ch for ch in value if ch.isdigit())
    if not digits.startswith("55"):
        raise ValueError("Informe o WhatsApp com DDI 55, DDD e número. Ex: 5511999999999")
    return digits


async def provision(args: argparse.Namespace) -> None:
    validate_password_strength(args.admin_password)
    tenant_id = uuid.uuid4()
    instance_name = args.instance_name or f"saas_tenant_{tenant_id}"
    whatsapp = normalize_phone(args.whatsapp)
    owner_whatsapp = normalize_phone(args.owner_whatsapp or args.whatsapp)

    async with AsyncSessionLocal() as db:
        await db.execute(text("SET LOCAL app.bypass_rls = 'true'"))

        existing_user = (await db.execute(
            select(Usuario).where(Usuario.email == args.admin_email)
        )).scalar_one_or_none()
        if existing_user:
            raise RuntimeError(f"Já existe usuário com e-mail {args.admin_email}.")

        existing_instance = (await db.execute(
            select(Tenant).where(Tenant.evolution_instance_name == instance_name)
        )).scalar_one_or_none()
        if existing_instance:
            raise RuntimeError(f"Já existe tenant com instância {instance_name}.")

        tenant = Tenant(
            id=tenant_id,
            nome=args.nome,
            tipo=args.tipo,
            whatsapp_numero=whatsapp,
            owner_whatsapp=owner_whatsapp,
            evolution_instance_name=instance_name,
            plano=args.plano,
            sistema_ativo=True,
            horario_abertura=args.abertura,
            horario_fechamento=args.fechamento,
            limite_pedido_grande=args.limite,
            cor_primaria=args.cor,
        )
        db.add(tenant)
        await db.flush()

        await db.execute(text("SELECT set_tenant_id(:tenant_id)"), {"tenant_id": tenant_id})

        user = Usuario(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            nome=args.admin_nome,
            email=args.admin_email,
            senha_hash=get_password_hash(args.admin_password),
            perfil="dono",
        )
        db.add(user)

        config = Configuracao(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            limite_pedido_grande=args.limite,
            mensagem_boas_vindas=f"Olá! Seja bem-vindo(a) à {args.nome}. Como podemos ajudar?",
            mensagem_fora_horario=f"Olá! A {args.nome} está fora do horário de atendimento. Retornaremos assim que possível.",
            mensagem_confirmacao="Podemos confirmar seu horário?",
            mensagem_reativacao=f"Olá! Sentimos sua falta na {args.nome}. Quer agendar um retorno?",
        )
        db.add(config)

        if args.tipo == "clinica" and args.default_services:
            for service_name, category, duration in DEFAULT_CLINIC_SERVICES:
                db.add(ServicoProduto(
                    id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    nome=service_name,
                    categoria=category,
                    duracao_minutos=duration,
                    ativo=True,
                ))

        await db.commit()

    print("\nTenant provisionado com sucesso!\n")
    print(f"TENANT_ID={tenant_id}")
    print(f"NOME={args.nome}")
    print(f"TIPO={args.tipo}")
    print(f"ADMIN_EMAIL={args.admin_email}")
    print("ADMIN_PASSWORD definida com sucesso (nao exibida).")
    print(f"EVOLUTION_INSTANCE_NAME={instance_name}")
    print("\nVariáveis sugeridas para o frontend/Vercel deste cliente:")
    print(f"VITE_TENANT_ID={tenant_id}")
    print(f"VITE_TENANT_NOME={args.nome}")
    print(f"VITE_TENANT_TIPO={args.tipo}")
    print(f"VITE_TENANT_COR_PRIMARIA={args.cor}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Provisiona um novo cliente/tenant.")
    parser.add_argument("--nome", required=True, help="Nome da clínica/empresa.")
    parser.add_argument("--tipo", choices=["clinica", "loja"], default="clinica")
    parser.add_argument("--whatsapp", required=True, help="WhatsApp comercial com DDI. Ex: 5511999999999")
    parser.add_argument("--owner-whatsapp", help="WhatsApp do dono/responsável por alertas.")
    parser.add_argument("--instance-name", help="Nome exato da instância na Evolution API.")
    parser.add_argument("--admin-nome", default="Administrador")
    parser.add_argument("--admin-email", required=True)
    parser.add_argument("--admin-password", required=True)
    parser.add_argument("--plano", choices=["starter", "pro", "premium"], default="starter")
    parser.add_argument("--cor", default="#2563eb")
    parser.add_argument("--abertura", default="08:00")
    parser.add_argument("--fechamento", default="18:00")
    parser.add_argument("--limite", type=int, default=10)
    parser.add_argument("--no-default-services", dest="default_services", action="store_false")
    parser.set_defaults(default_services=True)
    return parser


if __name__ == "__main__":
    asyncio.run(provision(build_parser().parse_args()))
