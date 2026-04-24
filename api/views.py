import json
import math
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from datetime import timedelta

from core.models import UserProfile, Category, Course
from api.utils import parse_json_body, require_admin, error_response, json_response, hash_password, create_notification


@require_http_methods(['GET'])
def get_users(request):
    """
    GET /api/admin/users
    Query params: school_level, year_level, course, status, sort, page, limit
    """
    admin_school_id = require_admin(request)
    if not admin_school_id:
        return error_response('Admin authentication required', 401)

    school_level = request.GET.get('school_level', 'all').strip()
    year_level = request.GET.get('year_level', '').strip()
    course = request.GET.get('course', '').strip()
    status = request.GET.get('status', 'all').strip()
    sort = request.GET.get('sort', 'newest').strip()
    page = int(request.GET.get('page', 1))
    limit = min(int(request.GET.get('limit', 100)), 100)

    if page < 1:
        page = 1
    if limit < 1:
        limit = 100

    queryset = UserProfile.objects.filter(is_staff=False)

    if school_level and school_level != 'all':
        queryset = queryset.filter(school_level=school_level)

    if year_level:
        queryset = queryset.filter(year_level=year_level)

    if course:
        queryset = queryset.filter(course=course)

    if status and status != 'all':
        queryset = queryset.filter(status=status)

    if sort == 'az':
        queryset = queryset.order_by('name')
    elif sort == 'za':
        queryset = queryset.order_by('-name')
    elif sort == 'school_id':
        queryset = queryset.order_by('school_id')
    else:
        queryset = queryset.order_by('-created_at')

    total = queryset.count()
    offset = (page - 1) * limit
    users = queryset[offset:offset + limit]

    users_list = []
    for user in users:
        users_list.append({
            'school_id': user.school_id,
            'name': user.name,
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
        })

    total_pages = math.ceil(total / limit) if limit > 0 else 0

    return json_response({
        'data': users_list,
        'pagination': {
            'page': page,
            'limit': limit,
            'total': total,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_prev': page > 1
        },
        'filters_applied': {
            'school_level': school_level,
            'year_level': year_level,
            'course': course,
            'status': status
        }
    }, 200)


@require_http_methods(['GET'])
def get_users_summary(request):
    """
    GET /api/admin/users/summary
    Returns counts per category for dashboard display
    """
    admin_school_id = require_admin(request)
    if not admin_school_id:
        return error_response('Admin authentication required', 401)

    total_students = UserProfile.objects.filter(is_staff=False).count()

    high_school_total = UserProfile.objects.filter(is_staff=False, school_level='High School').count()
    grade_7 = UserProfile.objects.filter(is_staff=False, school_level='High School', year_level='Grade 7').count()
    grade_8 = UserProfile.objects.filter(is_staff=False, school_level='High School', year_level='Grade 8').count()
    grade_9 = UserProfile.objects.filter(is_staff=False, school_level='High School', year_level='Grade 9').count()
    grade_10 = UserProfile.objects.filter(is_staff=False, school_level='High School', year_level='Grade 10').count()

    college_total = UserProfile.objects.filter(is_staff=False, school_level='College').count()
    college_by_course = {}
    college_by_year = {}

    for course_obj in Course.objects.all():
        count = UserProfile.objects.filter(is_staff=False, school_level='College', course=course_obj.name).count()
        if count > 0:
            college_by_course[course_obj.name] = count

    for year in ['1st Year', '2nd Year', '3rd Year', '4th Year']:
        count = UserProfile.objects.filter(is_staff=False, school_level='College', year_level=year).count()
        if count > 0:
            college_by_year[year] = count

    pending_registrations = UserProfile.objects.filter(is_staff=False, status='pending').count()
    expired_accounts = UserProfile.objects.filter(is_staff=False, status='expired').count()

    return json_response({
        'total_students': total_students,
        'high_school': {
            'total': high_school_total,
            'grade_7': grade_7,
            'grade_8': grade_8,
            'grade_9': grade_9,
            'grade_10': grade_10
        },
        'college': {
            'total': college_total,
            'by_course': college_by_course,
            'by_year': college_by_year
        },
        'pending_registrations': pending_registrations,
        'expired_accounts': expired_accounts
    }, 200)


@require_http_methods(['POST'])
def renew_account(request):
    """
    POST /api/admin/users/renew
    Body: { school_id, extend_years }
    """
    admin_school_id = require_admin(request)
    if not admin_school_id:
        return error_response('Admin authentication required', 401)

    body = parse_json_body(request)
    if not body:
        return error_response('Invalid JSON', 400)

    school_id = body.get('school_id', '').strip()
    extend_years = body.get('extend_years')

    if not school_id or extend_years is None:
        return error_response('school_id and extend_years are required', 400)

    try:
        user = UserProfile.objects.get(school_id=school_id)
    except UserProfile.DoesNotExist:
        return error_response('User not found', 404)

    try:
        admin = UserProfile.objects.get(school_id=admin_school_id)
    except UserProfile.DoesNotExist:
        return error_response('Admin not found', 404)

    now = timezone.now()

    if user.account_expires_at is None:
        new_expiry = now + timedelta(days=365 * extend_years)
    else:
        new_expiry = max(user.account_expires_at, now) + timedelta(days=365 * extend_years)

    user.account_expires_at = new_expiry
    user.expiry_notified = False
    user.account_status_detail = 'active'
    user.status = 'approved'
    user.save()

    create_notification(
        recipient_school_id=school_id,
        notification_type='account_expiry_warning',
        title='Account Renewed',
        message=f'Your library account has been renewed by {admin.name}. New expiry: {new_expiry.strftime("%Y-%m-%d")}.',
        sent_by=admin_school_id
    )

    return json_response({
        'success': True,
        'new_expiry': new_expiry.isoformat()
    }, 200)


@require_http_methods(['GET'])
def ping(request):
    """
    GET /api/ping
    Returns status of API and database
    """
    try:
        from django.db import connection
        connection.ensure_connection()
        db_ok = True
    except Exception:
        db_ok = False

    return json_response({
        'ok': True,
        'db': db_ok,
        'time': timezone.now().isoformat()
    }, 200)


@require_http_methods(['GET'])
def get_courses(request):
    """
    GET /api/courses
    Returns all Course names
    """
    courses = Course.objects.all().values_list('name', flat=True)
    return json_response({
        'courses': list(courses)
    }, 200)


@require_http_methods(['POST'])
def create_category(request):
    """
    POST /api/admin/categories/create
    Body: { name }
    """
    admin_school_id = require_admin(request)
    if not admin_school_id:
        return error_response('Admin authentication required', 401)

    body = parse_json_body(request)
    if not body:
        return error_response('Invalid JSON', 400)

    name = body.get('name', '').strip()
    if not name:
        return error_response('name is required', 400)

    if Category.objects.filter(name=name).exists():
        return error_response('Category already exists', 409)

    category = Category.objects.create(name=name)

    return json_response({
        'success': True,
        'category': {
            'name': category.name,
            'created_at': category.created_at.isoformat()
        }
    }, 201)


@require_http_methods(['POST'])
def rename_category(request):
    """
    POST /api/admin/categories/rename
    Body: { old_name, new_name }
    """
    admin_school_id = require_admin(request)
    if not admin_school_id:
        return error_response('Admin authentication required', 401)

    body = parse_json_body(request)
    if not body:
        return error_response('Invalid JSON', 400)

    old_name = body.get('old_name', '').strip()
    new_name = body.get('new_name', '').strip()

    if not old_name or not new_name:
        return error_response('old_name and new_name are required', 400)

    try:
        category = Category.objects.get(name=old_name)
    except Category.DoesNotExist:
        return error_response('Category not found', 404)

    if Category.objects.filter(name=new_name).exists():
        return error_response('New category name already exists', 409)

    from core.models import Book
    Book.objects.filter(category=old_name).update(category=new_name)

    category.name = new_name
    category.save()

    return json_response({
        'success': True,
        'category': {
            'name': category.name,
            'updated_at': category.created_at.isoformat()
        }
    }, 200)


@require_http_methods(['POST'])
def delete_category(request):
    """
    POST /api/admin/categories/delete
    Body: { name, confirm: false (default) }
    """
    admin_school_id = require_admin(request)
    if not admin_school_id:
        return error_response('Admin authentication required', 401)

    body = parse_json_body(request)
    if not body:
        return error_response('Invalid JSON', 400)

    name = body.get('name', '').strip()
    confirm = body.get('confirm', False)

    if not name:
        return error_response('name is required', 400)

    try:
        category = Category.objects.get(name=name)
    except Category.DoesNotExist:
        return error_response('Category not found', 404)

    from core.models import Book
    book_count = Book.objects.filter(category=name).count()

    if not confirm and book_count > 0:
        return json_response({
            'warning': True,
            'book_count': book_count,
            'message': f'This category has {book_count} books. Deleting it will also delete all those books. Confirm?'
        }, 200)

    if confirm:
        Book.objects.filter(category=name).delete()

    category.delete()

    return json_response({
        'success': True,
        'books_deleted': book_count if confirm else 0
    }, 200)
