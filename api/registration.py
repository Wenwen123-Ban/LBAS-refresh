import json
import uuid
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from datetime import timedelta

from core.models import UserProfile, RegistrationRequest, Notification
from api.utils import (
    parse_json_body, require_admin, error_response, json_response,
    hash_password, create_notification
)


@require_http_methods(['POST'])
def register_request(request):
    """
    POST /api/register_request
    
    Body: {
        school_id, name, password, year_level, school_level, category,
        course (optional), phone_number (optional), email (optional)
    }
    
    Validates required fields, course required if College,
    year_level must be Grade 7/8/9/10 if High School
    """
    body = parse_json_body(request)
    if not body:
        return error_response('Invalid JSON', 400)

    required_fields = ['school_id', 'name', 'password', 'year_level', 'school_level', 'category']
    for field in required_fields:
        if field not in body or not str(body.get(field, '')).strip():
            return error_response(f'{field} is required', 400)

    school_id = body.get('school_id', '').strip()
    name = body.get('name', '').strip()
    password = body.get('password', '').strip()
    year_level = body.get('year_level', '').strip()
    school_level = body.get('school_level', '').strip()
    category = body.get('category', '').strip()
    course = body.get('course', '').strip()
    phone_number = body.get('phone_number', '').strip()
    email = body.get('email', '').strip()

    if school_level == 'College' and not course:
        return error_response('course is required for College students', 400)

    if school_level == 'High School' and year_level not in ['Grade 7', 'Grade 8', 'Grade 9', 'Grade 10']:
        return error_response('Invalid year_level for High School', 400)

    if UserProfile.objects.filter(school_id=school_id).exists():
        return error_response('school_id already registered', 409)

    if RegistrationRequest.objects.filter(school_id=school_id, status='pending').exists():
        return error_response('Pending registration request already exists for this school_id', 409)

    request_id = f"REG-{uuid.uuid4().hex[:12]}"
    request_number = str(RegistrationRequest.objects.count() + 1).zfill(10)
    pending_expires_at = timezone.now() + timedelta(hours=48)

    RegistrationRequest.objects.create(
        request_id=request_id,
        request_number=request_number,
        name=name,
        school_id=school_id,
        password=password,
        year_level=year_level,
        school_level=school_level,
        category=category,
        course=course,
        phone_number=phone_number,
        email=email,
        pending_expires_at=pending_expires_at
    )

    return json_response({
        'success': True,
        'request_number': request_number,
        'request_id': request_id
    }, 201)


@require_http_methods(['GET'])
def get_registration_requests(request):
    """
    GET /api/admin/registration-requests
    Returns all registration requests ordered by created_at desc
    """
    admin_school_id = require_admin(request)
    if not admin_school_id:
        return error_response('Admin authentication required', 401)

    requests = RegistrationRequest.objects.all().order_by('-created_at')

    requests_list = []
    for reg_req in requests:
        requests_list.append({
            'request_id': reg_req.request_id,
            'request_number': reg_req.request_number,
            'name': reg_req.name,
            'school_id': reg_req.school_id,
            'year_level': reg_req.year_level,
            'school_level': reg_req.school_level,
            'category': reg_req.category,
            'course': reg_req.course,
            'phone_number': reg_req.phone_number,
            'email': reg_req.email,
            'status': reg_req.status,
            'reviewed_by': reg_req.reviewed_by,
            'reviewed_at': reg_req.reviewed_at.isoformat() if reg_req.reviewed_at else None,
            'created_at': reg_req.created_at.isoformat()
        })

    return json_response({
        'requests': requests_list
    }, 200)


@require_http_methods(['POST'])
def registration_decision(request, request_id):
    """
    POST /api/admin/registration-requests/<request_id>/decision
    
    Body: { decision: "approve" or "reject" }
    
    If approve: create UserProfile, hash password, set status=approved
    If reject: update request status=rejected
    """
    admin_school_id = require_admin(request)
    if not admin_school_id:
        return error_response('Admin authentication required', 401)

    body = parse_json_body(request)
    if not body:
        return error_response('Invalid JSON', 400)

    decision = body.get('decision', '').lower()
    if decision not in ['approve', 'reject']:
        return error_response('decision must be "approve" or "reject"', 400)

    try:
        reg_req = RegistrationRequest.objects.get(request_id=request_id)
    except RegistrationRequest.DoesNotExist:
        return error_response('Registration request not found', 404)

    if reg_req.status != 'pending':
        return error_response('Request is no longer pending', 400)

    admin_user = UserProfile.objects.get(school_id=admin_school_id)

    if decision == 'approve':
        account_expires_at = calculate_account_expiry(reg_req.year_level, reg_req.school_level)

        UserProfile.objects.create(
            school_id=reg_req.school_id,
            name=reg_req.name,
            password=hash_password(reg_req.password),
            is_staff=False,
            status='approved',
            category=reg_req.category,
            school_level=reg_req.school_level,
            year_level=reg_req.year_level,
            course=reg_req.course,
            phone_number=reg_req.phone_number,
            email=reg_req.email,
            photo=reg_req.photo,
            account_expires_at=account_expires_at,
            account_status_detail='active'
        )

        reg_req.status = 'approved'
        reg_req.reviewed_by = admin_school_id
        reg_req.reviewed_at = timezone.now()
        reg_req.save()

        create_notification(
            recipient_school_id=reg_req.school_id,
            notification_type='registration_approved',
            title='Registration Approved',
            message=f'Your registration has been approved by {admin_user.name}. You can now log in to the library system.',
            sent_by=admin_school_id
        )

        return json_response({
            'success': True,
            'message': 'Registration approved'
        }, 200)

    else:
        reg_req.status = 'rejected'
        reg_req.reviewed_by = admin_school_id
        reg_req.reviewed_at = timezone.now()
        reg_req.save()

        return json_response({
            'success': True,
            'message': 'Registration rejected'
        }, 200)


@require_http_methods(['POST'])
def register_student(request):
    """
    POST /api/register_student
    Admin direct register — no queue, creates UserProfile directly
    
    Body: {
        school_id, name, password, year_level, school_level, category,
        course (optional), phone_number (optional), email (optional)
    }
    """
    admin_school_id = require_admin(request)
    if not admin_school_id:
        return error_response('Admin authentication required', 401)

    body = parse_json_body(request)
    if not body:
        return error_response('Invalid JSON', 400)

    required_fields = ['school_id', 'name', 'password', 'year_level', 'school_level', 'category']
    for field in required_fields:
        if field not in body or not str(body.get(field, '')).strip():
            return error_response(f'{field} is required', 400)

    school_id = body.get('school_id', '').strip()
    name = body.get('name', '').strip()
    password = body.get('password', '').strip()
    year_level = body.get('year_level', '').strip()
    school_level = body.get('school_level', '').strip()
    category = body.get('category', '').strip()
    course = body.get('course', '').strip()
    phone_number = body.get('phone_number', '').strip()
    email = body.get('email', '').strip()

    if school_level == 'College' and not course:
        return error_response('course is required for College students', 400)

    if UserProfile.objects.filter(school_id=school_id).exists():
        return error_response('school_id already registered', 409)

    account_expires_at = calculate_account_expiry(year_level, school_level)

    UserProfile.objects.create(
        school_id=school_id,
        name=name,
        password=hash_password(password),
        is_staff=False,
        status='approved',
        category=category,
        school_level=school_level,
        year_level=year_level,
        course=course,
        phone_number=phone_number,
        email=email,
        account_expires_at=account_expires_at,
        account_status_detail='active'
    )

    return json_response({
        'success': True,
        'school_id': school_id,
        'message': 'Student registered successfully'
    }, 201)


def calculate_account_expiry(year_level, school_level):
    """Calculate account expiry date based on year_level and school_level."""
    now = timezone.now()

    if school_level == 'High School':
        if year_level == 'Grade 7':
            return now + timedelta(days=365 * 4)
        elif year_level == 'Grade 8':
            return now + timedelta(days=365 * 3)
        elif year_level == 'Grade 9':
            return now + timedelta(days=365 * 2)
        elif year_level == 'Grade 10':
            return now + timedelta(days=365)
    elif school_level == 'College':
        if year_level == '1st Year':
            return now + timedelta(days=365 * 4)
        elif year_level == '2nd Year':
            return now + timedelta(days=365 * 3)
        elif year_level == '3rd Year':
            return now + timedelta(days=365 * 2)
        elif year_level == '4th Year':
            return now + timedelta(days=365)

    return now
