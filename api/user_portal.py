import json
import math
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from core.models import Transaction, UserProfile, Session
from api.utils import parse_json_body, require_auth, error_response, json_response


@require_http_methods(['GET'])
def get_my_transactions(request):
    """
    GET /api/my/transactions
    Auth: student required
    Returns all transactions for logged-in student, ordered by date_reserved desc
    """
    student_id = require_auth(request)
    if not student_id:
        return error_response('Authentication required', 401)

    page = int(request.GET.get('page', 1))
    limit = min(int(request.GET.get('limit', 30)), 30)

    if page < 1:
        page = 1
    if limit < 1:
        limit = 30

    transactions = Transaction.objects.filter(
        student_id=student_id
    ).order_by('-date_reserved')

    total = transactions.count()
    offset = (page - 1) * limit
    paginated_transactions = transactions[offset:offset + limit]

    transactions_list = []
    for txn in paginated_transactions:
        transactions_list.append({
            'transaction_id': str(txn.transaction_id),
            'book_no': txn.book_no,
            'book_title': txn.book_title,
            'status': txn.status,
            'date_reserved': txn.date_reserved.isoformat(),
            'is_approved': txn.is_approved,
            'approved_by_name': txn.approved_by_name,
            'date_approved': txn.date_approved.isoformat() if txn.date_approved else None,
            'pickup_deadline': txn.pickup_deadline.isoformat() if txn.pickup_deadline else None,
            'pickup_location': txn.pickup_location,
            'date_borrowed': txn.date_borrowed.isoformat() if txn.date_borrowed else None,
            'return_due_date': txn.return_due_date.isoformat() if txn.return_due_date else None,
            'date_returned': txn.date_returned.isoformat() if txn.date_returned else None,
            'queue_position': txn.queue_position,
            'reservation_note': txn.reservation_note
        })

    total_pages = math.ceil(total / limit) if limit > 0 else 0

    return json_response({
        'data': transactions_list,
        'pagination': {
            'page': page,
            'limit': limit,
            'total': total,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_prev': page > 1
        }
    }, 200)


@require_http_methods(['GET'])
def get_my_profile(request):
    """
    GET /api/my/profile
    Auth: student required
    Returns own UserProfile
    """
    student_id = require_auth(request)
    if not student_id:
        return error_response('Authentication required', 401)

    try:
        user = UserProfile.objects.get(school_id=student_id)
    except UserProfile.DoesNotExist:
        # Support built-in/local admin sessions (for example: developer/dev)
        # that may exist in Session table without a persisted UserProfile row.
        auth_header = request.headers.get('Authorization', '')
        token = auth_header[7:] if auth_header.startswith('Bearer ') else auth_header
        session = Session.objects.filter(token=token, school_id=student_id).first()
        if not session:
            return error_response('User not found', 404)

        profile_payload = {
            'school_id': student_id,
            'name': student_id,
            'is_staff': bool(session.is_staff),
            'category': 'admin' if session.is_staff else None,
            'school_level': None,
            'year_level': None,
            'course': None,
            'phone_number': None,
            'email': None,
            'photo': None,
            'status': 'approved',
            'account_status_detail': 'active',
            'account_expires_at': session.expires_at.isoformat() if session.expires_at else None,
            'created_at': session.created_at.isoformat() if session.created_at else None
        }

        response_payload = dict(profile_payload)
        response_payload['profile'] = profile_payload
        return json_response(response_payload, 200)

    profile_payload = {
        'school_id': user.school_id,
        'name': user.name,
        'is_staff': user.is_staff,
        'category': user.category,
        'school_level': user.school_level,
        'year_level': user.year_level,
        'course': user.course,
        'phone_number': user.phone_number,
        'email': user.email,
        'photo': user.photo,
        'status': user.status,
        'account_status_detail': user.account_status_detail,
        'account_expires_at': user.account_expires_at.isoformat() if user.account_expires_at else None,
        'created_at': user.created_at.isoformat()
    }

    # Backward-compatible response shape for both frontends:
    # - flat fields (current dashboard scripts)
    # - nested profile object (older consumers)
    response_payload = dict(profile_payload)
    response_payload['profile'] = profile_payload

    return json_response(response_payload, 200)


@require_http_methods(['POST'])
def update_profile_photo(request):
    """
    POST /api/my/profile/update-photo
    Auth: student required
    Body: { avatar }
    Updates photo field
    """
    student_id = require_auth(request)
    if not student_id:
        return error_response('Authentication required', 401)

    body = parse_json_body(request)
    if not body:
        return error_response('Invalid JSON', 400)

    avatar = body.get('avatar', '').strip()
    if not avatar:
        return error_response('avatar is required', 400)

    try:
        user = UserProfile.objects.get(school_id=student_id)
    except UserProfile.DoesNotExist:
        return error_response('User not found', 404)

    user.photo = avatar
    user.save()

    return json_response({
        'success': True,
        'photo': user.photo
    }, 200)
