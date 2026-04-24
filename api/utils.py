import json
from django.http import JsonResponse
from django.utils import timezone
from datetime import timedelta
import bcrypt
import secrets
from core.models import Session, UserProfile, Transaction, Book, Notification
from django.db.models import Q


def require_auth(request):
    auth_header = request.headers.get('Authorization', '')
    # Accept both "Bearer <token>" and raw token
    if auth_header.startswith('Bearer '):
        token = auth_header[7:]
    else:
        token = auth_header
    if not token:
        return None
    try:
        session = Session.objects.get(token=token, expires_at__gt=timezone.now())
        return session.school_id
    except Session.DoesNotExist:
        return None

def require_admin(request):
    """
    Extract and validate admin auth token from request.
    Returns school_id if valid and is_staff, None otherwise.
    """
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return None
    
    token = auth_header[7:]
    
    try:
        session = Session.objects.get(token=token, expires_at__gt=timezone.now(), is_staff=True)
        return session.school_id
    except Session.DoesNotExist:
        return None


def parse_json_body(request):
    """
    Parse JSON request body.
    Returns dict if successful, None if request is not JSON or parsing fails.
    """
    try:
        return json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return None


def hash_password(password):
    """Hash a password using bcrypt."""
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')


def verify_password(password, hashed):
    """Verify a password against bcrypt hash."""
    try:
        return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False


def generate_token():
    """Generate a secure random token."""
    return secrets.token_urlsafe(50)


def calculate_deadline(value, unit):
    """
    Calculate a deadline from now + value of unit.
    unit: "minutes", "hours", "days", "weeks", "months"
    """
    now = timezone.now()
    
    if unit == 'minutes':
        return now + timedelta(minutes=value)
    elif unit == 'hours':
        return now + timedelta(hours=value)
    elif unit == 'days':
        return now + timedelta(days=value)
    elif unit == 'weeks':
        return now + timedelta(weeks=value)
    elif unit == 'months':
        return now + timedelta(days=value * 30)
    else:
        return now


def create_notification(recipient_school_id, notification_type, title, message, 
                       related_transaction_id=None, related_book_no=None, sent_by=None):
    """Create a notification for a user."""
    notification = Notification.objects.create(
        recipient_school_id=recipient_school_id,
        notification_type=notification_type,
        title=title,
        message=message,
        related_transaction_id=related_transaction_id,
        related_book_no=related_book_no,
        sent_by=sent_by
    )
    return notification


def recalculate_book_status(book_no):
    """
    Recalculate book status based on active transactions.
    """
    active = Transaction.objects.filter(
        book_no=book_no,
        status__in=['Pending', 'Reserved', 'Borrowed', 'Unreturned']
    ).order_by('created_at')
    
    if active.filter(status='Borrowed').exists():
        new_status = 'Borrowed'
    elif active.filter(status='Unreturned').exists():
        new_status = 'Unreturned'
    elif active.filter(status='Reserved').exists():
        new_status = 'Reserved'
    elif active.filter(status='Pending').exists():
        new_status = 'Pending'
    else:
        new_status = 'Available'
    
    Book.objects.filter(book_no=book_no).update(status=new_status)


def json_response(data, status=200):
    """Return a JSON response."""
    return JsonResponse(data, status=status)


def error_response(message, status=400):
    """Return a JSON error response."""
    return JsonResponse({'error': message}, status=status)


def resolve_cover(filename):
    """Resolve cover image filename to full URL path."""
    if not filename or filename == 'default_book.jpg':
        return '/static/images/default_book.jpg'
    return f'/static/images/covers/{filename}'
