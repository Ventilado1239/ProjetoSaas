import json
import uuid
from sqlalchemy import event, text
from sqlalchemy.orm import Session
from app.models.models import ClientePaciente, AtendimentoPedido, LogAuditoria
from app.utils.context import current_user_var, tenant_id_var

@event.listens_for(Session, "after_begin")
def set_tenant_on_begin(session, transaction, connection):
    tid = tenant_id_var.get()
    if tid:
        connection.execute(
            text("SELECT set_tenant_id(:tenant_id)"),
            {"tenant_id": tid}
        )
    else:
        connection.execute(text("SELECT set_tenant_id(NULL)"))


def serialize_row(obj):
    """Serialize database model columns to a dictionary of primitive types."""
    res = {}
    for col in obj.__table__.columns:
        val = getattr(obj, col.name)
        if val is None:
            res[col.name] = None
        elif isinstance(val, uuid.UUID):
            res[col.name] = str(val)
        elif hasattr(val, "isoformat"):
            res[col.name] = val.isoformat()
        elif isinstance(val, (int, float, bool, str)):
            res[col.name] = val
        else:
            res[col.name] = str(val)
    return res

def get_changes(obj):
    """Detect added and deleted values on a dirty object's columns."""
    state = obj._sa_instance_state
    old_vals = {}
    new_vals = {}
    
    for attr in state.mapper.attrs:
        hist = state.get_history(attr.key, True)
        if hist.has_changes():
            old_val = hist.deleted[0] if hist.deleted else None
            new_val = hist.added[0] if hist.added else getattr(obj, attr.key)
            
            # Serialize old value
            if isinstance(old_val, uuid.UUID):
                old_val = str(old_val)
            elif hasattr(old_val, "isoformat"):
                old_val = old_val.isoformat()
                
            # Serialize new value
            if isinstance(new_val, uuid.UUID):
                new_val = str(new_val)
            elif hasattr(new_val, "isoformat"):
                new_val = new_val.isoformat()
                
            old_vals[attr.key] = old_val
            new_vals[attr.key] = new_val
            
    return old_vals, new_vals

@event.listens_for(Session, "before_flush")
def before_flush(session, flush_context, instances):
    user = current_user_var.get()
    user_id = user.id if user else None
    user_email = user.email if user else "system"
    
    logs = []
    
    # 1. New objects (INSERT)
    for obj in session.new:
        if isinstance(obj, (ClientePaciente, AtendimentoPedido)):
            tenant_id = getattr(obj, "tenant_id", None)
            if not tenant_id and user:
                tenant_id = user.tenant_id
                
            if tenant_id:
                new_vals = serialize_row(obj)
                
                log_entry = LogAuditoria(
                    id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    usuario_id=user_id,
                    usuario_email=user_email,
                    acao="INSERT",
                    tabela=obj.__tablename__,
                    registro_id=obj.id,
                    valores_antigos=None,
                    valores_novos=json.dumps(new_vals)
                )
                logs.append(log_entry)

    # 2. Dirty/Modified objects (UPDATE)
    for obj in session.dirty:
        if isinstance(obj, (ClientePaciente, AtendimentoPedido)):
            state = obj._sa_instance_state
            if not state.has_identity:
                continue
                
            old_vals, new_vals = get_changes(obj)
            if not old_vals and not new_vals:
                continue
                
            tenant_id = getattr(obj, "tenant_id", None)
            if not tenant_id and user:
                tenant_id = user.tenant_id
                
            if tenant_id:
                log_entry = LogAuditoria(
                    id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    usuario_id=user_id,
                    usuario_email=user_email,
                    acao="UPDATE",
                    tabela=obj.__tablename__,
                    registro_id=obj.id,
                    valores_antigos=json.dumps(old_vals),
                    valores_novos=json.dumps(new_vals)
                )
                logs.append(log_entry)

    # 3. Deleted objects (DELETE)
    for obj in session.deleted:
        if isinstance(obj, (ClientePaciente, AtendimentoPedido)):
            tenant_id = getattr(obj, "tenant_id", None)
            if not tenant_id and user:
                tenant_id = user.tenant_id
                
            if tenant_id:
                is_lgpd = getattr(obj, "_lgpd_delete", False)
                if is_lgpd:
                    acao = "LGPD_DELETE"
                    old_vals = {"info": "Dados apagados por requisicao LGPD (direito ao esquecimento)."}
                else:
                    acao = "DELETE"
                    old_vals = serialize_row(obj)
                
                log_entry = LogAuditoria(
                    id=uuid.uuid4(),
                    tenant_id=tenant_id,
                    usuario_id=user_id,
                    usuario_email=user_email,
                    acao=acao,
                    tabela=obj.__tablename__,
                    registro_id=obj.id,
                    valores_antigos=json.dumps(old_vals),
                    valores_novos=None
                )
                logs.append(log_entry)

    for log in logs:
        session.add(log)
