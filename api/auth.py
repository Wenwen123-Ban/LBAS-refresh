import json
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from datetime import timedelta

from core.models import UserProfile, Session
from api.utils import parse_json_body, generate_token, verify_password, error_response, json_response


@require_http_methods(['POST'])
def login(request):
    """
    POST /api/login
    Body: { school_id, password (optional), id_only }
    
    id_only=True: student login, no password check
    id_only=False: admin login, check password hash
    """
    body = parse_json_body(request)
    if not body:
        return error_response('Invalid JSON', 400)

    school_id = body.get('school_id', '').strip()
    password = body.get('password', '')
    id_only = body.get('id_only', False)

    if not school_id:
        return error_response('school_id is required', 400)

    try:
        user = UserProfile.objects.get(school_id=school_id)
    except UserProfile.DoesNotExist:
        return error_response('User not found', 404)

    if user.status != 'approved':
        return error_response('Account is not approved', 403)

    if id_only and user.is_staff:
        return error_response('Students cannot use id_only login', 403)

    if not id_only and not user.is_staff:
        return error_response('Students must use id_only login', 403)

    if not id_only and not verify_password(password, user.password):
        return error_response('Invalid password', 401)

    token = generate_token()
    expires_at = timezone.now() + timedelta(hours=2)

    Session.objects.create(
        token=token,
        school_id=school_id,
        is_staff=user.is_staff,
        expires_at=expires_at
    )

    profile = {
        'school_id': user.school_id,
        'name': user.name,
        'is_staff': user.is_staff,
        'category': user.category,
        'school_level': user.school_level,
        'year_level': user.year_level,
        'course': user.course,
        'photo': user.photo,
        'email': user.email,
        'phone_number': user.phone_number,
    }

    return json_response({
        'token': token,
        'profile': profile,
        'expires_at': expires_at.isoformat()
    }, 200)


@require_http_methods(['POST'])
def logout(request):
    """
    POST /api/logout
    Delete session by token
    """
    auth_header = request.headers.get('Authorization', '')
    if not auth_header.startswith('Bearer '):
        return error_response('Authorization header required', 401)

    token = auth_header[7:]

    try:
        session = Session.objects.get(token=token)
        session.delete()
        return json_response({'success': True}, 200)
    except Session.DoesNotExist:
        return error_response('Session not found', 404)
