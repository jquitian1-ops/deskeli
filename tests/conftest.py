"""
Pytest configuration and fixtures for TicketDesk tests
"""
import pytest
import os
import tempfile
import sys
from datetime import datetime, timedelta

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app import app, db, User, Company, Ticket, TokenBlacklist, AuditLog, UserSession


@pytest.fixture
def client():
    """Create test client with temporary database"""
    # Create temporary database
    db_fd, db_path = tempfile.mkstemp(suffix='.db')
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{db_path}'
    app.config['TESTING'] = True
    app.config['SECRET_KEY'] = 'test-secret-key'

    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()

    os.close(db_fd)
    os.unlink(db_path)


@pytest.fixture
def runner(client):
    """Create CLI runner for Flask"""
    return app.test_cli_runner()


@pytest.fixture
def setup_test_data(client):
    """Setup test data: companies, users, tickets"""
    with app.app_context():
        # Create companies
        eliot = Company(code='eliot', name='Manufactureras Eliot', users_limit=100)
        pash = Company(code='pash', name='Pash', users_limit=100)
        primatela = Company(code='primatela', name='Primatela', users_limit=100)

        db.session.add_all([eliot, pash, primatela])
        db.session.commit()

        # Create users
        admin_user = User(
            username='admin_eliot',
            email='admin@eliot.local',
            password_hash='hashed_password_123',
            role='admin',
            company_id=eliot.id
        )
        tech_user = User(
            username='tech_eliot',
            email='tech@eliot.local',
            password_hash='hashed_password_123',
            role='technician',
            company_id=eliot.id
        )
        emp_user = User(
            username='emp_eliot',
            email='emp@eliot.local',
            password_hash='hashed_password_123',
            role='employee',
            company_id=eliot.id
        )

        db.session.add_all([admin_user, tech_user, emp_user])
        db.session.commit()

        # Create tickets
        ticket1 = Ticket(
            company_id=eliot.id,
            ticket_number='TKT-001',
            title='Test Ticket 1',
            description='Test description',
            priority='high',
            status='open',
            created_by=emp_user.id,
            assigned_to=tech_user.id,
            created_at=datetime.utcnow(),
            version=1
        )
        ticket2 = Ticket(
            company_id=eliot.id,
            ticket_number='TKT-002',
            title='Test Ticket 2',
            description='Another test',
            priority='critical',
            status='open',
            created_by=emp_user.id,
            assigned_to=None,
            created_at=datetime.utcnow(),
            version=1
        )

        db.session.add_all([ticket1, ticket2])
        db.session.commit()

        return {
            'companies': {'eliot': eliot, 'pash': pash, 'primatela': primatela},
            'users': {'admin': admin_user, 'tech': tech_user, 'emp': emp_user},
            'tickets': {'ticket1': ticket1, 'ticket2': ticket2}
        }


@pytest.fixture
def auth_token(client, setup_test_data):
    """Generate JWT token for testing"""
    import jwt
    from datetime import datetime, timedelta

    user = setup_test_data['users']['admin']
    payload = {
        'user_id': user.id,
        'username': user.username,
        'role': user.role,
        'company_id': user.company_id,
        'exp': datetime.utcnow() + timedelta(hours=1)
    }
    token = jwt.encode(payload, app.config['SECRET_KEY'], algorithm='HS256')
    return token


@pytest.fixture
def headers_authenticated(auth_token):
    """Headers with JWT token"""
    return {
        'Authorization': f'Bearer {auth_token}',
        'Content-Type': 'application/json'
    }
