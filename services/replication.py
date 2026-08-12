"""Servicio de propagación Eliot → Pash + Primatela.

Cuando un admin asigna subroles o guiones a un técnico/admin de la empresa
'eliot', el sistema busca si el mismo email existe como usuario en 'pash' y
'primatela' y le replica automáticamente las asignaciones equivalentes.

- Subroles: si el subrol es global (company IS NULL) se asigna directo. Si
  es propio de eliot, se busca por nombre en la empresa destino; si no
  existe, se clona en la empresa destino y luego se asigna.
- Guiones: se busca por nombre (case-insensitive) en la empresa destino; si
  no existe, se clona con código sufijado (-pash / -primatela) incluyendo
  todas sus subtareas (assignees re-resueltos por email dentro de la
  empresa destino).

La dirección es siempre eliot → otras. No propaga al revés.

Los imports de app y modelos se hacen lazy (dentro de las funciones) para
evitar dependencia circular durante la carga del módulo.
"""
from __future__ import annotations


REPLICATE_TARGETS = ('pash', 'primatela')


def find_peer_users(source_user):
    """Devuelve la lista de usuarios activos con el mismo email en pash+primatela."""
    from app import db, User  # lazy import para evitar ciclo
    if not source_user or not source_user.email:
        return []
    email_l = source_user.email.strip().lower()
    return User.query.filter(
        db.func.lower(User.email) == email_l,
        User.company.in_(REPLICATE_TARGETS),
        User.role.in_(('technician', 'admin')),
        User.is_active == True,
    ).all()


def replicate_subroles_to_peers(source_user, subrole_ids):
    """source_user está en 'eliot'. Replica sus subroles a los peers en pash+primatela.

    Retorna {'peers': int, 'assigned': int}.
    """
    from app import db, Subrole, UserSubrole
    if not source_user or source_user.company != 'eliot':
        return {'peers': 0, 'assigned': 0}
    peers = find_peer_users(source_user)
    if not peers:
        return {'peers': 0, 'assigned': 0}

    source_subroles = [Subrole.query.get(sid) for sid in (subrole_ids or [])]
    source_subroles = [s for s in source_subroles if s and s.is_active]
    total_assigned = 0

    for peer in peers:
        # Reemplaza asignaciones existentes del peer (mismo modelo que el set original)
        UserSubrole.query.filter_by(user_id=peer.id).delete()
        for src in source_subroles:
            target_subrole = None
            if src.company is None:
                # Global — asignar el mismo directamente
                target_subrole = src
            elif src.company == 'eliot':
                # Buscar equivalente por nombre en la empresa peer
                target_subrole = Subrole.query.filter(
                    db.func.lower(Subrole.name) == src.name.strip().lower(),
                    Subrole.company == peer.company,
                    Subrole.is_active == True,
                ).first()
                if not target_subrole:
                    # Clonar el subrol en la empresa peer
                    target_subrole = Subrole(
                        name=src.name,
                        description=src.description,
                        icon=src.icon,
                        company=peer.company,
                        is_system=False,
                        is_active=True,
                    )
                    db.session.add(target_subrole)
                    db.session.flush()
            else:
                continue
            db.session.add(UserSubrole(user_id=peer.id, subrole_id=target_subrole.id))
            total_assigned += 1

    return {'peers': len(peers), 'assigned': total_assigned}


def replicate_guiones_to_peers(source_user, guion_ids):
    """source_user está en 'eliot'. Replica sus guiones (y las plantillas si faltan)
    a los peers en pash+primatela.

    Retorna {'peers': int, 'assigned': int, 'cloned_guiones': int}.
    """
    from app import db, User, Guion, GuionSubtask, UserGuion
    if not source_user or source_user.company != 'eliot':
        return {'peers': 0, 'assigned': 0, 'cloned_guiones': 0}
    peers = find_peer_users(source_user)
    if not peers:
        return {'peers': 0, 'assigned': 0, 'cloned_guiones': 0}

    source_guiones = [Guion.query.get(gid) for gid in (guion_ids or [])]
    source_guiones = [g for g in source_guiones if g and g.company == 'eliot']
    total_assigned = 0
    total_cloned = 0

    for peer in peers:
        # Reemplaza asignaciones existentes del peer (mismo modelo que el set original)
        UserGuion.query.filter_by(user_id=peer.id).delete()
        for src in source_guiones:
            # Buscar equivalente por nombre (case-insensitive) en la empresa peer
            target = Guion.query.filter(
                db.func.lower(Guion.name) == src.name.strip().lower(),
                Guion.company == peer.company,
            ).first()
            if not target:
                # Clonar guión + subtareas
                base_code = src.code
                new_code = f'{base_code}-{peer.company}'[:50]
                # Asegurar unicidad global del code (raro, pero por si ya existe)
                suffix = 1
                while Guion.query.filter_by(code=new_code).first():
                    suffix += 1
                    new_code = f'{base_code}-{peer.company}{suffix}'[:50]
                target = Guion(
                    code=new_code,
                    name=src.name[:200],
                    description=src.description,
                    company=peer.company,
                    default_priority=src.default_priority,
                    default_category=src.default_category,
                    is_active=src.is_active,
                    created_by_id=source_user.id,
                )
                db.session.add(target)
                db.session.flush()
                # Clonar subtareas resolviendo assignees por email en la empresa peer
                src_subs = GuionSubtask.query.filter_by(guion_id=src.id).order_by(GuionSubtask.order_idx).all()
                for s in src_subs:
                    assignee_id = None
                    if s.assignee and s.assignee.email:
                        u = User.query.filter(
                            db.func.lower(User.email) == s.assignee.email.strip().lower(),
                            User.company == peer.company,
                            User.role.in_(('technician', 'admin')),
                            User.is_active == True,
                        ).first()
                        assignee_id = u.id if u else None
                    db.session.add(GuionSubtask(
                        guion_id=target.id,
                        order_idx=s.order_idx,
                        title=s.title,
                        description=s.description,
                        category=s.category,
                        priority=s.priority,
                        assignee_id=assignee_id,
                    ))
                total_cloned += 1

            if target.is_active:
                db.session.add(UserGuion(user_id=peer.id, guion_id=target.id))
                total_assigned += 1

    return {'peers': len(peers), 'assigned': total_assigned, 'cloned_guiones': total_cloned}
