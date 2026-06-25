#!/usr/bin/env python3
"""
TicketDesk Agent Orchestrator v1.0
4 agentes especializados para clasificación, asignación, respuesta y escalación automática de tickets.
Sin LLM (modo reglas). Switch a Claude API cuando ANTHROPIC_API_KEY esté disponible.
"""
import os
import json
import time
import re
from datetime import datetime, timedelta
from threading import Thread
import logging
from dotenv import load_dotenv

# Cargar variables de entorno desde .env
load_dotenv()

logger = logging.getLogger('orchestrator')

# ═════════════════════════════════════════════════════════════════════════════
# SWITCH LLM — Activación automática con ANTHROPIC_API_KEY
# ═════════════════════════════════════════════════════════════════════════════

ANTHROPIC_API_KEY = os.getenv('ANTHROPIC_API_KEY', '').strip()
USE_LLM = bool(ANTHROPIC_API_KEY and (ANTHROPIC_API_KEY.startswith('sk-ant-') or ANTHROPIC_API_KEY.startswith('sk-')))
_anthropic_client = None

print(f"[agents.py] ANTHROPIC_API_KEY presente: {bool(ANTHROPIC_API_KEY)}")
print(f"[agents.py] USE_LLM activado: {USE_LLM}")

def _try_import_anthropic():
    """Importar anthropic solo si la clave es válida y el paquete está instalado."""
    if not USE_LLM:
        return None
    try:
        import anthropic
        return anthropic.Anthropic(api_key=ANTHROPIC_API_KEY)
    except ImportError:
        logger.warning('[Orchestrator] anthropic no instalado. Usando reglas.')
        return None
    except Exception as e:
        logger.warning(f'[Orchestrator] Error al inicializar Anthropic: {e}. Usando reglas.')
        return None

if USE_LLM:
    _anthropic_client = _try_import_anthropic()


# ═════════════════════════════════════════════════════════════════════════════
# DICCIONARIOS DE PALABRAS CLAVE
# ═════════════════════════════════════════════════════════════════════════════

CATEGORY_KEYWORDS = {
    'Red': ['wifi', 'red', 'internet', 'conexion', 'conectar', 'vpn', 'lan', 'router',
            'switch', 'ping', 'dns', 'ip', 'firewall', 'cable', 'conectividad'],
    'Hardware': ['computadora', 'pc', 'laptop', 'teclado', 'mouse', 'monitor', 'pantalla',
                 'impresora', 'scanner', 'disco', 'memoria', 'ram', 'procesador', 'cpu',
                 'bateria', 'cargador', 'usb', 'puerto', 'equipo'],
    'Software': ['software', 'programa', 'aplicacion', 'instalar', 'desinstalar', 'actualizar',
                 'licencia', 'error', 'falla', 'crash', 'bloquea', 'no abre', 'lento'],
    'Email': ['correo', 'email', 'outlook', 'bandeja', 'adjunto', 'spam', 'smtp', 'imap', 'gmail'],
    'SAP': ['sap', 'erp', 'transaccion', 'modulo', 'pedido', 'factura', 'contabilidad',
            'inventario', 'logistica', 'mm', 'sd', 'fi', 'co', 'hr'],
    'Seguridad': ['virus', 'malware', 'ransomware', 'phishing', 'acceso', 'permiso',
                  'contrasena', 'cuenta', 'bloqueado', 'hackeo', 'sospechoso'],
    'Telefonia': ['telefono', 'celular', 'movil', 'extension', 'voip', 'llamada', 'sip'],
    'Servidor': ['servidor', 'server', 'caido', 'servicio', 'reiniciar', 'bd', 'base de datos',
                 'backup', 'almacenamiento', 'nube', 'azure', 'aws'],
}

URGENCY_KEYWORDS = {
    'critical': ['urgente', 'critico', 'critica', 'parado', 'caido', 'no funciona', 'bloqueado',
                 'perdida', 'produccion', 'sap caido', 'sin acceso', 'datos perdidos'],
    'high': ['importante', 'rapido', 'pronto', 'afecta', 'varios usuarios', 'equipo', 'necesito'],
    'low': ['cuando puedas', 'sin prisa', 'cuando tengas tiempo', 'eventual', 'mejora'],
}

RESPONSE_TEMPLATES = {
    'Red': "Hemos recibido tu ticket sobre conectividad. Mientras se revisa: verifica conexiones físicas, reinicia tu adaptador de red. ¿Otros equipos tienen conexión?",
    'Hardware': "Tu reporte de falla de hardware fue registrado. Evita apagar/encender repetidamente el equipo. Anota cualquier error visual o sonido que observes.",
    'Software': "Recibimos tu reporte. Como primer paso: cierra y reabre la aplicación. Si el error persiste, anota el mensaje exacto para el técnico.",
    'Email': "Ticket de correo recibido. Verifica que Outlook esté actualizado y que tu contraseña no haya expirado. El equipo de mensajería estará en contacto.",
    'SAP': "Incidencia SAP registrada. NO realices más transacciones sobre el registro afectado hasta confirmación de técnico. Equipo ERP notificado.",
    'Seguridad': "IMPORTANTE: Tu reporte fue escalado. NO abras más archivos sospechosos, desconecta si hay riesgo. Equipo de seguridad responde urgente.",
    'General': "Tu solicitud fue recibida. Un técnico la revisará según el SLA configurado. Puedes hacer seguimiento desde tu portal.",
}

# Palabras clave permitidas para el Bot de Soporte Tecnológico 1
SUPPORT_SCOPE_KEYWORDS = {
    'allowed': [
        # Red y conectividad
        'wifi', 'red', 'internet', 'conexion', 'conectar', 'vpn', 'dns', 'ip',
        # Hardware
        'computadora', 'pc', 'laptop', 'monitor', 'teclado', 'mouse', 'impresora', 'disco',
        # Email y comunicaciones
        'correo', 'email', 'outlook', 'smtp', 'smtp', 'mensajeria',
        # Software básico
        'software', 'aplicacion', 'programa', 'instalar', 'desinstalar', 'actualizar', 'licencia',
        # Soporte técnico general
        'soporte', 'tecnico', 'ayuda', 'problema', 'error', 'falla', 'no funciona', 'como',
        'configurar', 'restablecer', 'contraseña', 'password', 'acceso', 'permisos',
        # Windows y Office
        'windows', 'office', 'word', 'excel', 'powerpoint', 'windows 10', 'windows 11',
        # SAP (incluido en soporte permitido)
        'sap', 'transaccion', 'modulo', 'reporte', 'usuario sap',
    ],
    'forbidden': [
        'payroll', 'nomina', 'seguridad critica', 'hacking', 'virus',
        'produccion', 'base de datos', 'servidor',
    ]
}


# ═════════════════════════════════════════════════════════════════════════════
# AGENTE 0: VALIDADOR DE SCOPE (Bot de Soporte Tecnológico 1)
# ═════════════════════════════════════════════════════════════════════════════

class AgentBotResponder:
    """Genera respuestas usando Claude API para el bot de soporte."""

    NAME = 'bot_responder'

    def run(self, question: str) -> dict:
        """Genera respuesta inteligente. Retorna {answer, source, confidence, used_llm}"""
        start = time.time()

        if _anthropic_client:
            result = self._run_with_llm(question)
        else:
            result = self._run_with_rules(question)

        result['duration_ms'] = int((time.time() - start) * 1000)
        result['used_llm'] = bool(_anthropic_client)
        return result

    def _run_with_llm(self, question: str) -> dict:
        """Generar respuesta con Claude."""
        prompt = f"""Eres un asistente de soporte tecnologico para empleados.
Responde BREVEMENTE (máximo 5 párrafos, máximo 500 caracteres) en español.

IMPORTANTE: Solo responde sobre estos temas de SOPORTE TECNOLOGICO 1:
- Red e Internet (WiFi, DNS, VPN, conectividad)
- Hardware (PC, laptop, monitor, impresora, teclado)
- Email y Outlook
- Software básico (instalación, actualización)
- Windows (contraseñas, acceso, permisos)

Si la pregunta es sobre SAP, nómina, seguridad crítica, bases de datos u otros temas especializados, RECHAZA amablemente.

Pregunta del usuario: {question}

Responde directamente sin prólogo."""

        try:
            message = _anthropic_client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=256,
                messages=[{"role": "user", "content": prompt}]
            )
            answer = message.content[0].text.strip()

            # Verificar si Claude rechazó la pregunta
            if any(word in answer.lower() for word in ['fuera', 'especializado', 'no puedo', 'no cubre', 'alcance']):
                return {
                    'answer': answer,
                    'source': 'claude_rejected',
                    'confidence': 80
                }

            return {
                'answer': answer,
                'source': 'claude',
                'confidence': 85
            }
        except Exception as e:
            logger.error(f'[BotResponder LLM] {e}')
            return self._run_with_rules(question)

    def _run_with_rules(self, question: str) -> dict:
        """Fallback a respuesta genérica."""
        return {
            'answer': 'Disculpa, no pude generar una respuesta automática. Te recomiendo crear un ticket para que nuestro equipo revise tu situación.',
            'source': 'fallback',
            'confidence': 30
        }


class AgentScopeValidator:
    """Valida que la pregunta esté dentro del scope de Soporte Tecnológico 1."""

    NAME = 'scope_validator'

    def validate(self, question: str) -> dict:
        """
        Retorna {is_valid, message, confidence}
        is_valid=True si la pregunta está dentro del scope, False si no.
        """
        question_lower = question.lower()

        # Verificar palabras clave prohibidas primero (strict)
        forbidden_matches = sum(1 for kw in SUPPORT_SCOPE_KEYWORDS['forbidden']
                               if kw in question_lower)
        if forbidden_matches > 0:
            return {
                'is_valid': False,
                'message': "❌ Tu pregunta está fuera del alcance del Soporte Tecnológico 1. "
                          "Este servicio solo cubre: redes, hardware, email, software básico y Windows. "
                          "Para otros temas, por favor crea un ticket con el equipo especializado.",
                'confidence': 95,
                'scope': 'out_of_scope'
            }

        # Verificar palabras clave permitidas
        allowed_matches = sum(1 for kw in SUPPORT_SCOPE_KEYWORDS['allowed']
                             if kw in question_lower)

        if allowed_matches > 0:
            return {
                'is_valid': True,
                'message': None,
                'confidence': min(95, 40 + (allowed_matches * 10)),
                'scope': 'in_scope'
            }

        # Pregunta genérica - aceptar pero con baja confianza
        return {
            'is_valid': True,
            'message': None,
            'confidence': 30,
            'scope': 'generic'
        }


# ═════════════════════════════════════════════════════════════════════════════
# AGENTE 1: CLASIFICADOR
# ═════════════════════════════════════════════════════════════════════════════

class AgentClassifier:
    """Clasifica categoría y prioridad de un ticket."""

    NAME = 'classifier'

    def run(self, title: str, description: str, company: str) -> dict:
        """Retorna {category, priority, confidence, keywords_found, duration_ms, used_llm}"""
        start = time.time()
        if _anthropic_client:
            result = self._run_with_llm(title, description)
        else:
            result = self._run_with_rules(title, description)
        result['duration_ms'] = int((time.time() - start) * 1000)
        result['used_llm'] = bool(_anthropic_client)
        return result

    def _run_with_rules(self, title: str, description: str) -> dict:
        text = f"{title} {description}".lower()
        category_scores = {}
        for cat, keywords in CATEGORY_KEYWORDS.items():
            hits = [k for k in keywords if k in text]
            if hits:
                category_scores[cat] = len(hits)

        if category_scores:
            best_cat = max(category_scores, key=category_scores.get)
            total_hits = sum(category_scores.values())
            confidence = min(95, int((category_scores[best_cat] / max(total_hits, 1)) * 100) + 30)
        else:
            best_cat = 'General'
            confidence = 20

        detected_priority = None
        for priority, kws in URGENCY_KEYWORDS.items():
            if any(kw in text for kw in kws):
                detected_priority = priority
                break
        priority = detected_priority or 'medium'

        return {
            'category': best_cat,
            'priority': priority,
            'confidence': confidence,
            'keywords_found': list(category_scores.keys()) if category_scores else [],
        }

    def _run_with_llm(self, title: str, description: str) -> dict:
        """Clasificación con Claude API."""
        prompt = f"""Clasifica este ticket de soporte TI. Responde SOLO JSON válido.
Título: {title}
Descripción: {description}
JSON: {{"category": "Red|Hardware|Software|Email|SAP|Seguridad|Telefonia|Servidor|General",
        "priority": "low|medium|high|critical",
        "confidence": 0-100}}"""
        try:
            message = _anthropic_client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=256,
                messages=[{"role": "user", "content": prompt}]
            )
            raw = message.content[0].text.strip()
            return json.loads(raw)
        except Exception as e:
            logger.error(f'[Classifier LLM] {e}')
            return self._run_with_rules(title, description)


# ═════════════════════════════════════════════════════════════════════════════
# AGENTE 2: ASIGNADOR
# ═════════════════════════════════════════════════════════════════════════════

class AgentAssignor:
    """Asignación inteligente usando TechnicianProfile."""

    NAME = 'assignor'

    def run(self, ticket, db_session) -> dict:
        """Retorna {technician_id, technician_name, confidence, reason, duration_ms, used_llm}"""
        start = time.time()
        from app import User, TechnicianProfile

        techs = User.query.filter_by(
            company=ticket.company,
            role='technician',
            is_active=True
        ).all()

        if not techs:
            return {
                'technician_id': None, 'confidence': 0,
                'reason': 'Sin técnicos disponibles',
                'duration_ms': int((time.time() - start) * 1000),
                'used_llm': False
            }

        category = (ticket.category or 'General').lower()
        scores = {}
        details = {}

        for tech in techs:
            profile = TechnicianProfile.query.filter_by(user_id=tech.id).first()
            active_load = len([t for t in tech.assigned_tickets
                               if t.status in ['open', 'in_progress']])
            score = active_load * 3

            if profile:
                if not profile.is_available:
                    score += 9999
                if active_load >= profile.max_tickets:
                    score += 999

                skills = profile.get_skills_list()
                if category in skills:
                    level = profile.get_skill_level(category)
                    skill_bonus = -int(level / 10)
                    score += skill_bonus
                    details[tech.id] = f"habilidad={category}(niv:{level}), carga={active_load}"
                else:
                    details[tech.id] = f"sin habilidad en {category}, carga={active_load}"
            else:
                if category in tech.name.lower():
                    score -= 5
                details[tech.id] = f"sin perfil, carga={active_load}"

            scores[tech.id] = score

        best_id = min(scores, key=scores.get)
        best_tech = next(t for t in techs if t.id == best_id)

        has_skill = 'habilidad=' in details.get(best_id, '')
        confidence = 85 if has_skill else 55

        return {
            'technician_id': best_id,
            'technician_name': best_tech.name,
            'confidence': confidence,
            'reason': details.get(best_id, ''),
            'duration_ms': int((time.time() - start) * 1000),
            'used_llm': False
        }


# ═════════════════════════════════════════════════════════════════════════════
# AGENTE 3: RESPONDEDOR
# ═════════════════════════════════════════════════════════════════════════════

class AgentResponder:
    """Genera respuesta inicial automática."""

    NAME = 'responder'

    def run(self, ticket, db_session) -> dict:
        """Retorna {message, source, confidence, duration_ms, used_llm}"""
        start = time.time()
        if _anthropic_client:
            result = self._run_with_llm(ticket)
        else:
            result = self._run_with_rules(ticket, db_session)
        result['duration_ms'] = int((time.time() - start) * 1000)
        result['used_llm'] = bool(_anthropic_client)
        return result

    def _run_with_rules(self, ticket, db_session) -> dict:
        from app import BotKnowledge
        text = f"{ticket.title} {ticket.description}".lower()

        knowledge = BotKnowledge.query.all()
        best_kb = None
        best_score = 0
        for kb in knowledge:
            keywords = [k.strip().lower() for k in kb.keywords.split(',')]
            score = sum(2 for k in keywords if k in text)
            if score > best_score:
                best_score = score
                best_kb = kb

        if best_kb and best_score >= 2:
            msg = f"{best_kb.answer}\n\nSi esto no resuelve tu problema, un técnico revisará pronto."
            return {'message': msg, 'source': 'kb_match', 'confidence': 75}

        category = ticket.category or 'General'
        template = RESPONSE_TEMPLATES.get(category, RESPONSE_TEMPLATES['General'])
        return {'message': template, 'source': 'template', 'confidence': 60}

    def _run_with_llm(self, ticket) -> dict:
        """Generación con Claude API."""
        prompt = f"""Respuesta inicial BREVE (máx 3 párrafos) en español para ticket IT:
Categoría: {ticket.category}
Prioridad: {ticket.priority}
Título: {ticket.title}
Descripción: {ticket.description[:300]}"""
        try:
            message = _anthropic_client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}]
            )
            return {
                'message': message.content[0].text.strip(),
                'source': 'llm',
                'confidence': 88
            }
        except Exception as e:
            logger.error(f'[Responder LLM] {e}')
            return self._run_with_rules(ticket, None)


# ═════════════════════════════════════════════════════════════════════════════
# AGENTE 4: ESCALADOR (THREAD DAEMON)
# ═════════════════════════════════════════════════════════════════════════════

class AgentEscalator:
    """Monitorea tickets activos cada 5 min. Escala si SLA>=80% sin actividad."""

    NAME = 'escalator'
    CHECK_INTERVAL_SECONDS = 300
    INACTIVITY_THRESHOLD_MINUTES = 30
    BLOCKED_THRESHOLD_MINUTES = 120

    def __init__(self, flask_app, db_instance):
        self.app = flask_app
        self.db = db_instance
        self._thread = None
        self._running = False

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._running = True
        self._thread = Thread(target=self._loop, daemon=True, name='AgentEscalator')
        self._thread.start()
        logger.info('[Escalator] Thread iniciado.')

    def stop(self):
        self._running = False

    def _loop(self):
        """Loop principal del escalator. Garantiza app_context en cada iteración
        y captura la traceback completa si algo falla (no solo el mensaje)."""
        import traceback
        # Pequeño delay inicial para que la app termine de inicializar todo
        time.sleep(15)
        while self._running:
            try:
                with self.app.app_context():
                    try:
                        self._check_all_active_tickets()
                    except Exception as inner:
                        logger.error(f'[Escalator] Error en check: {type(inner).__name__}: {inner}')
                        logger.error(f'[Escalator] Traceback:\n{traceback.format_exc()}')
            except Exception as outer:
                logger.error(f'[Escalator] Error en context: {type(outer).__name__}: {outer}')
            # Esperar el intervalo configurado AL FINAL de la iteración
            time.sleep(self.CHECK_INTERVAL_SECONDS)

    def _check_all_active_tickets(self):
        # Usar self.db (referencia que se pasó al construir) en vez de re-importar
        from app import Ticket, Message
        db = self.db
        now = datetime.now()
        # Excluir tickets internos del sistema (DMs, chats grupales)
        active = db.session.query(Ticket).filter(
            Ticket.status.in_(['open', 'in_progress']),
            Ticket.sla_deadline.isnot(None),
            ~Ticket.ticket_number.like('DM-%'),
            ~Ticket.ticket_number.like('CHAT-%'),
        ).all()

        for ticket in active:
            try:
                total_sla = ticket.sla_minutes or 120
                elapsed = (now - ticket.created_at).total_seconds() / 60
                pct_used = (elapsed / total_sla) * 100 if total_sla > 0 else 0

                last_msg = db.session.query(Message).filter_by(ticket_id=ticket.id)\
                    .order_by(Message.created_at.desc()).first()
                last_activity = last_msg.created_at if last_msg else (ticket.updated_at or ticket.created_at)
                minutes_inactive = (now - last_activity).total_seconds() / 60

                should_escalate = (pct_used >= 80 and minutes_inactive >= self.INACTIVITY_THRESHOLD_MINUTES)
                is_blocked = (ticket.assignee_id is not None and
                              minutes_inactive >= self.BLOCKED_THRESHOLD_MINUTES and
                              ticket.status == 'in_progress')

                if should_escalate or is_blocked:
                    self._escalate(ticket, pct_used, is_blocked)
            except Exception as e:
                logger.error(f'[Escalator] Error procesando ticket {ticket.id}: {e}')
                # Continuar con el siguiente ticket, no detener el loop

    def _escalate(self, ticket, pct_used, is_blocked):
        from app import Message, AgentAction, User, log_audit, emit_ticket_event
        db = self.db
        try:
            reason = 'bloqueado sin actualización' if is_blocked else f'SLA al {int(pct_used)}%'
            sys_user = db.session.query(User).filter_by(role='admin', company=ticket.company).first()
            if not sys_user:
                return

            # Evitar escalar el mismo ticket repetidamente: chequear si ya hay
            # una acción de escalación reciente (últimos 30 min)
            recent_escalation = db.session.query(AgentAction).filter(
                AgentAction.ticket_id == ticket.id,
                AgentAction.agent_name == self.NAME,
                AgentAction.created_at >= (datetime.now() - timedelta(minutes=30))
            ).first()
            if recent_escalation:
                return  # ya se escaló recientemente

            msg_text = f"[ALERTA] Ticket escalado automáticamente: {reason}. Revisa urgente."
            new_msg = Message(ticket_id=ticket.id, user_id=sys_user.id, text=msg_text)
            db.session.add(new_msg)

            action = AgentAction(
                ticket_id=ticket.id, company=ticket.company,
                agent_name=self.NAME, action_type='escalate',
                input_data=json.dumps({'pct_used': pct_used, 'is_blocked': is_blocked}),
                output_data=json.dumps({'reason': reason}),
                confidence=90, used_llm=False, success=True
            )
            db.session.add(action)
            db.session.commit()

            log_audit('agent_escalate', None, 'ticket', ticket.id, f'[Escalator] {reason}')
            emit_ticket_event(ticket.company, 'sla_escalated', {
                'ticket_number': ticket.ticket_number,
                'reason': reason
            })
            logger.info(f'[Escalator] Ticket {ticket.ticket_number} escalado: {reason}')
        except Exception as e:
            db.session.rollback()
            logger.error(f'[Escalator] Error escalando ticket {ticket.id}: {e}')


# ═════════════════════════════════════════════════════════════════════════════
# ORCHESTRATOR CENTRAL
# ═════════════════════════════════════════════════════════════════════════════

class AgentOrchestrator:
    """Coordina los 4 agentes. Hook principal desde employee_create."""

    def __init__(self, flask_app, db_instance):
        self.app = flask_app
        self.db = db_instance
        self.classifier = AgentClassifier()
        self.assignor = AgentAssignor()
        self.responder = AgentResponder()
        self.escalator = AgentEscalator(flask_app, db_instance)
        self._status = {
            'classifier': {'last_run': None, 'last_success': None, 'total_runs': 0, 'errors': 0},
            'assignor':   {'last_run': None, 'last_success': None, 'total_runs': 0, 'errors': 0},
            'responder':  {'last_run': None, 'last_success': None, 'total_runs': 0, 'errors': 0},
            'escalator':  {'last_run': None, 'last_success': None, 'total_runs': 0, 'errors': 0},
        }

    def start_background_agents(self):
        self.escalator.start()

    def process_new_ticket(self, ticket) -> dict:
        """Hook principal. Clasificar → Asignar → Responder."""
        results = {}
        try:
            results['classify']  = self._run_agent('classifier', ticket)
            results['assign']    = self._run_agent('assignor',   ticket)
            results['respond']   = self._run_agent('responder',  ticket)
        except Exception as e:
            logger.error(f'[Orchestrator] Error en ticket {ticket.id}: {e}')
        return results

    def _run_agent(self, agent_name: str, ticket) -> dict:
        from app import AgentAction, Message, User, db, log_audit, emit_ticket_event
        agent = getattr(self, agent_name)
        start = time.time()
        status = self._status[agent_name]
        status['total_runs'] += 1
        status['last_run'] = datetime.now().isoformat()

        try:
            if agent_name == 'classifier':
                result = agent.run(ticket.title, ticket.description, ticket.company)
                if result.get('confidence', 0) >= 60:
                    if result.get('category') and result['category'] != 'General':
                        ticket.category = result['category']
                    if result.get('priority') and ticket.priority == 'medium':
                        ticket.priority = result['priority']
                    db.session.commit()

            elif agent_name == 'assignor':
                result = agent.run(ticket, db.session)
                if result.get('technician_id') and not ticket.assignee_id:
                    ticket.assignee_id = result['technician_id']
                    db.session.commit()

            elif agent_name == 'responder':
                result = agent.run(ticket, db.session)
                if result.get('message'):
                    sys_user = User.query.filter_by(
                        role='admin', company=ticket.company
                    ).first()
                    if sys_user:
                        msg = Message(
                            ticket_id=ticket.id,
                            user_id=sys_user.id,
                            text=f"[Bot] {result['message']}"
                        )
                        db.session.add(msg)
                        db.session.commit()

            action = AgentAction(
                ticket_id=ticket.id,
                company=ticket.company,
                agent_name=agent_name,
                action_type=agent_name,
                input_data=json.dumps({'title': ticket.title[:100]}),
                output_data=json.dumps({k: v for k, v in result.items()
                                        if k not in ('score_detail',)}),
                confidence=result.get('confidence', 0),
                used_llm=result.get('used_llm', False),
                duration_ms=result.get('duration_ms', 0),
                success=True
            )
            db.session.add(action)
            db.session.commit()

            status['last_success'] = datetime.now().isoformat()
            return result

        except Exception as e:
            status['errors'] += 1
            logger.error(f'[{agent_name}] Error: {e}')
            try:
                action = AgentAction(
                    ticket_id=ticket.id, company=ticket.company,
                    agent_name=agent_name, action_type=agent_name,
                    success=False, error_msg=str(e)[:500],
                    duration_ms=int((time.time() - start) * 1000)
                )
                db.session.add(action)
                db.session.commit()
            except:
                pass
            return {}

    def get_dashboard_data(self, company: str) -> dict:
        """Datos para /admin/orchestrator."""
        try:
            from app import AgentAction, Ticket

            now = datetime.now()
            last_24h = now - timedelta(hours=24)

            recent_actions = AgentAction.query.filter(
                AgentAction.company == company,
                AgentAction.created_at >= last_24h
            ).order_by(AgentAction.created_at.desc()).limit(100).all()

            by_agent = {}
            for a in recent_actions:
                ag = a.agent_name
                if ag not in by_agent:
                    by_agent[ag] = {'total': 0, 'success': 0, 'avg_confidence': 0,
                                    'llm_used': 0, 'confidences': []}
                by_agent[ag]['total'] += 1
                if a.success:
                    by_agent[ag]['success'] += 1
                if a.used_llm:
                    by_agent[ag]['llm_used'] += 1
                if a.confidence:
                    by_agent[ag]['confidences'].append(a.confidence)

            for ag_data in by_agent.values():
                confs = ag_data.pop('confidences', [])
                ag_data['avg_confidence'] = int(sum(confs) / len(confs)) if confs else 0

            pending_review = Ticket.query.filter_by(
                company=company, status='open'
            ).filter(Ticket.assignee_id.isnot(None)).count()

        except Exception as e:
            logger.warning(f'[Orchestrator] Error getting dashboard data: {e}')
            # Retornar datos vacíos pero estructura válida
            by_agent = {}
            pending_review = 0
            recent_actions = []

        # Conteos totales históricos (todo el tiempo) por tipo de agente para la empresa
        try:
            from app import AgentAction as _AA
            total_classified = _AA.query.filter_by(company=company, agent_name='classifier').count()
            total_assigned   = _AA.query.filter_by(company=company, agent_name='assignor').count()
            total_responded  = _AA.query.filter_by(company=company, agent_name='responder').count()
            total_escalated  = _AA.query.filter_by(company=company, agent_name='escalator').count()
        except Exception:
            total_classified = total_assigned = total_responded = total_escalated = 0

        return {
            'mode': 'LLM (Claude API)' if USE_LLM else 'Reglas (sin API Key)',
            'use_llm': USE_LLM,
            'status_by_agent': self._status,
            'stats_24h': by_agent,
            'escalator_running': self.escalator._thread and self.escalator._thread.is_alive() if self.escalator._thread else False,
            'pending_review': pending_review,
            # Conteos planos para el dashboard (KPIs)
            'total_classified': total_classified,
            'total_assigned': total_assigned,
            'total_responded': total_responded,
            'total_escalated': total_escalated,
            'recent_actions': [{
                'id': a.id,
                'ticket_id': a.ticket_id,
                'agent_name': a.agent_name,
                'action_type': a.action_type,
                'agent': a.agent_name,  # compat
                'action': a.action_type,  # compat
                'confidence': a.confidence,
                'used_llm': a.used_llm,
                'success': a.success,
                'duration_ms': a.duration_ms,
                'details': f"Ticket #{a.ticket_id} · {('OK' if a.success else 'FAIL')}{' · LLM' if a.used_llm else ''}{(' · ' + str(a.confidence) + '%') if a.confidence else ''}{(' · ' + (a.output_data[:80] if a.output_data else ''))}",
                'created_at': a.created_at.strftime('%Y-%m-%d %H:%M:%S') if a.created_at else '',
            } for a in recent_actions[:20]]
        }


# Instancia global — se inicializa desde app.py
orchestrator = None
