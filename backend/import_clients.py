import argparse
import asyncio
import csv
import uuid
from datetime import date
from pathlib import Path

from sqlalchemy import select, text

from app.database import AsyncSessionLocal
from app.models.models import ClientePaciente, Tenant


def normalize_phone(value: str) -> str:
    digits = "".join(ch for ch in (value or "") if ch.isdigit())
    if not digits:
        raise ValueError("WhatsApp vazio.")
    if len(digits) in (10, 11):
        digits = f"55{digits}"
    if not digits.startswith("55"):
        raise ValueError(f"WhatsApp precisa ter DDI 55 ou DDD+número: {value}")
    return digits


def parse_date(value: str | None) -> date | None:
    if not value:
        return None
    value = value.strip()
    if not value:
        return None
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            from datetime import datetime
            return datetime.strptime(value, fmt).date()
        except ValueError:
            pass
    raise ValueError(f"Data inválida: {value}. Use YYYY-MM-DD ou DD/MM/YYYY.")


async def import_clients(args: argparse.Namespace) -> None:
    csv_path = Path(args.csv)
    if not csv_path.exists():
        raise FileNotFoundError(f"Arquivo não encontrado: {csv_path}")

    tenant_id = uuid.UUID(args.tenant_id)
    created = 0
    updated = 0
    skipped = 0

    async with AsyncSessionLocal() as db:
        await db.execute(text("SET LOCAL app.bypass_rls = 'true'"))
        tenant = await db.get(Tenant, tenant_id)
        if not tenant:
            raise RuntimeError(f"Tenant não encontrado: {tenant_id}")

        await db.execute(text("SELECT set_tenant_id(:tenant_id)"), {"tenant_id": tenant_id})

        with csv_path.open("r", encoding=args.encoding, newline="") as f:
            reader = csv.DictReader(f)
            required = {"nome", "whatsapp"}
            missing = required - set(reader.fieldnames or [])
            if missing:
                raise RuntimeError(f"CSV precisa das colunas: {', '.join(sorted(required))}. Faltando: {', '.join(sorted(missing))}")

            for row_number, row in enumerate(reader, start=2):
                nome = (row.get("nome") or "").strip()
                if not nome:
                    skipped += 1
                    print(f"Linha {row_number}: ignorada sem nome.")
                    continue

                try:
                    whatsapp = normalize_phone(row.get("whatsapp", ""))
                    data_nascimento = parse_date(row.get("data_nascimento"))
                except ValueError as exc:
                    skipped += 1
                    print(f"Linha {row_number}: ignorada ({exc})")
                    continue

                convenio = (row.get("convenio") or "").strip() or None

                existing = (await db.execute(
                    select(ClientePaciente).where(
                        ClientePaciente.tenant_id == tenant_id,
                        ClientePaciente.whatsapp == whatsapp,
                    )
                )).scalar_one_or_none()

                if existing:
                    if args.update_existing:
                        existing.nome = nome
                        existing.data_nascimento = data_nascimento
                        existing.convenio = convenio
                        updated += 1
                    else:
                        skipped += 1
                    continue

                db.add(ClientePaciente(
                    id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    nome=nome,
                    whatsapp=whatsapp,
                    data_nascimento=data_nascimento,
                    convenio=convenio,
                    total_atendimentos=0,
                    ticket_medio=0.0,
                    status_reativacao="ativo",
                ))
                created += 1

        await db.commit()

    print(f"Importação concluída para {tenant.nome}.")
    print(f"Criados: {created}")
    print(f"Atualizados: {updated}")
    print(f"Ignorados: {skipped}")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Importa clientes/pacientes para um tenant a partir de CSV.")
    parser.add_argument("--tenant-id", required=True)
    parser.add_argument("--csv", required=True, help="CSV com colunas: nome,whatsapp,data_nascimento,convenio")
    parser.add_argument("--encoding", default="utf-8-sig")
    parser.add_argument("--update-existing", action="store_true")
    return parser


if __name__ == "__main__":
    asyncio.run(import_clients(build_parser().parse_args()))
