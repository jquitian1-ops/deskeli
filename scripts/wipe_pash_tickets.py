"""
wipe_pash_tickets.py — Full wipe de tickets de Pash + reset de contador

Ejecutar desde la terminal del contenedor DeskEli en Coolify:
    python scripts/wipe_pash_tickets.py --confirm

Borra TODO lo transaccional de la empresa 'pash':
  - tickets, subtareas, adjuntos (BD + archivos en disco)
  - mensajes/comentarios
  - acciones de agentes
  - referencias en mailbox_emails (NULL, no borra el email)
  - audit_logs relacionados con tickets/subtareas de pash

Mantiene intocado: usuarios, guiones, api keys, configuración, plantillas,
tags, subroles y logs no relacionados con tickets.

El contador se resetea automáticamente porque get_next_ticket_number()
deriva del MÁXIMO existente. Al borrar todo, el próximo será TKT-PASH-00001.
"""
import os
import sys
import argparse

# Forzar carga del env antes de importar app
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

from app import (
    app, db,
    Ticket, Subtask, SubtaskAttachment, TicketAttachment,
    Message, AgentAction, MailboxEmail, AuditLog
)

# Verificacion adicional: si el usuario solo quiere limpiar el contador del
# Orchestrator de Pash sin borrar tickets, puede correr el modo 'orchestrator-only'
# con: python scripts/wipe_pash_tickets.py --only-orchestrator --confirm


COMPANY = 'pash'


def wipe(dry_run=False):
    with app.app_context():
        # ── 1) IDs de tickets de pash ──────────────────────────────
        ticket_ids = [t.id for t in Ticket.query.filter_by(company=COMPANY).all()]
        if not ticket_ids:
            print(f'[wipe] No hay tickets de {COMPANY}. Nada que borrar.')
            return

        subtask_ids = [
            s.id for s in Subtask.query.filter(Subtask.ticket_id.in_(ticket_ids)).all()
        ]

        print(f'[wipe] Tickets de {COMPANY}: {len(ticket_ids)}')
        print(f'[wipe] Subtareas asociadas:  {len(subtask_ids)}')

        # ── 2) Archivos físicos: adjuntos de subtareas ─────────────
        sub_atts = SubtaskAttachment.query.filter(
            SubtaskAttachment.subtask_id.in_(subtask_ids)
        ).all() if subtask_ids else []

        # ── 3) Archivos físicos: adjuntos de tickets ───────────────
        tick_atts = TicketAttachment.query.filter(
            TicketAttachment.ticket_id.in_(ticket_ids)
        ).all()

        total_files = len(sub_atts) + len(tick_atts)
        print(f'[wipe] Archivos adjuntos:    {total_files} (subtareas={len(sub_atts)}, tickets={len(tick_atts)})')

        # Conteos previos de otras tablas
        msg_n  = Message.query.filter(Message.ticket_id.in_(ticket_ids)).count()
        act_n  = AgentAction.query.filter(AgentAction.ticket_id.in_(ticket_ids)).count()
        me_n   = MailboxEmail.query.filter(MailboxEmail.ticket_id.in_(ticket_ids)).count()
        audit_ticket_n = AuditLog.query.filter(
            AuditLog.entity_type == 'ticket',
            AuditLog.entity_id.in_(ticket_ids)
        ).count()
        audit_sub_n = AuditLog.query.filter(
            AuditLog.entity_type == 'subtask',
            AuditLog.entity_id.in_(subtask_ids)
        ).count() if subtask_ids else 0

        print(f'[wipe] Mensajes:             {msg_n}')
        print(f'[wipe] Acciones agentes:     {act_n}')
        print(f'[wipe] Mailbox refs:         {me_n}  (se NULL-ifica, no se borra el email)')
        print(f'[wipe] Audit logs relacionados: {audit_ticket_n + audit_sub_n}')

        if dry_run:
            print('\n[wipe] DRY RUN — no se borro nada. Corre de nuevo con --confirm')
            return

        # ── 4) BORRAR archivos de disco ────────────────────────────
        upload_folder = app.config.get('TICKET_UPLOAD_FOLDER', '')
        deleted_files = 0
        for a in sub_atts + tick_atts:
            if not a.stored_name:
                continue
            fpath = os.path.join(upload_folder, a.stored_name)
            try:
                if os.path.exists(fpath):
                    os.remove(fpath)
                    deleted_files += 1
            except OSError as e:
                print(f'[wipe] Error borrando {fpath}: {e}')
        print(f'[wipe] Archivos borrados del disco: {deleted_files}/{total_files}')

        # ── 5) BORRAR filas de BD (orden FK-safe) ──────────────────
        if subtask_ids:
            SubtaskAttachment.query.filter(
                SubtaskAttachment.subtask_id.in_(subtask_ids)
            ).delete(synchronize_session=False)

        Subtask.query.filter(Subtask.ticket_id.in_(ticket_ids)).delete(synchronize_session=False)
        TicketAttachment.query.filter(TicketAttachment.ticket_id.in_(ticket_ids)).delete(synchronize_session=False)
        Message.query.filter(Message.ticket_id.in_(ticket_ids)).delete(synchronize_session=False)
        AgentAction.query.filter(AgentAction.ticket_id.in_(ticket_ids)).delete(synchronize_session=False)

        # Mailbox emails: NULL la ref al ticket (no borrar el email en sí)
        MailboxEmail.query.filter(MailboxEmail.ticket_id.in_(ticket_ids)).update(
            {MailboxEmail.ticket_id: None}, synchronize_session=False
        )

        # Audit logs de tickets/subtareas
        AuditLog.query.filter(
            AuditLog.entity_type == 'ticket',
            AuditLog.entity_id.in_(ticket_ids)
        ).delete(synchronize_session=False)
        if subtask_ids:
            AuditLog.query.filter(
                AuditLog.entity_type == 'subtask',
                AuditLog.entity_id.in_(subtask_ids)
            ).delete(synchronize_session=False)

        # Purgar TODOS los AgentAction residuales de la empresa (incluye huerfanos
        # cuyo ticket_id ya no existe). Esto pone en 0 el contador del Orchestrator.
        agent_actions_purged = AgentAction.query.filter(
            AgentAction.company == COMPANY
        ).delete(synchronize_session=False)
        if agent_actions_purged:
            print(f'[wipe] AgentActions residuales purgados: {agent_actions_purged}')

        # Finalmente los tickets
        Ticket.query.filter(Ticket.company == COMPANY).delete(synchronize_session=False)

        db.session.commit()

        # ── 6) Verificación ────────────────────────────────────────
        remaining = Ticket.query.filter_by(company=COMPANY).count()
        print(f'\n[wipe] ✅ Terminado. Tickets restantes de {COMPANY}: {remaining}')
        print(f'[wipe] El proximo ticket sera: TKT-PASH-00001')


def wipe_orchestrator_only(dry_run=False):
    """Limpieza acotada: solo purga los AgentAction del Orchestrator para Pash.
    NO borra tickets, subtareas, adjuntos ni nada mas.
    Util cuando el contador del dashboard quedo con basura pero los tickets estan OK."""
    with app.app_context():
        count = AgentAction.query.filter(AgentAction.company == COMPANY).count()
        print(f'[wipe-orch] AgentActions de {COMPANY}: {count}')
        if not count:
            print('[wipe-orch] Nada que purgar.')
            return
        if dry_run:
            print('[wipe-orch] DRY RUN — Corre con --confirm para purgar.')
            return
        AgentAction.query.filter(AgentAction.company == COMPANY).delete(synchronize_session=False)
        db.session.commit()
        print(f'[wipe-orch] ✅ Purgados {count} AgentAction de {COMPANY}. Contador del Orchestrator ahora en 0.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--confirm', action='store_true',
                        help='Ejecuta el borrado real. Sin este flag, hace dry-run.')
    parser.add_argument('--only-orchestrator', action='store_true',
                        help='Modo acotado: solo purga los AgentAction del Orchestrator para pash.')
    args = parser.parse_args()
    if args.only_orchestrator:
        wipe_orchestrator_only(dry_run=not args.confirm)
    else:
        wipe(dry_run=not args.confirm)
