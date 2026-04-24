import json
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
import math

from core.models import Notification
from api.utils import parse_json_body, require_auth, error_response, json_response


@require_http_methods(['GET'])
def get_notifications(request):
    """
    GET /api/my/notifications
    Auth: student required
    Returns notifications for logged-in student, ordered by created_at desc
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

    notifications = Notification.objects.filter(
        recipient_school_id=student_id
    ).order_by('-created_at')

    total = notifications.count()
    offset = (page - 1) * limit
    paginated_notifications = notifications[offset:offset + limit]

    notifications_list = []
    for notif in paginated_notifications:
        notifications_list.append({
            'notification_id': str(notif.notification_id),
            'notification_type': notif.notification_type,
            'title': notif.title,
            'message': notif.message,
            'related_transaction_id': str(notif.related_transaction_id) if notif.related_transaction_id else None,
            'related_book_no': notif.related_book_no,
            'is_read': notif.is_read,
            'created_at': notif.created_at.isoformat()
        })

    total_pages = math.ceil(total / limit) if limit > 0 else 0

    return json_response({
        'data': notifications_list,
        'pagination': {
            'page': page,
            'limit': limit,
            'total': total,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_prev': page > 1
        }
    }, 200)


@require_http_methods(['POST'])
def mark_notification_read(request):
    """
    POST /api/my/notifications/read
    Auth: student required
    Body: { notification_id } or { mark_all: true }
    Marks notification as read
    """
    student_id = require_auth(request)
    if not student_id:
        return error_response('Authentication required', 401)

    body = parse_json_body(request)
    if not body:
        return error_response('Invalid JSON', 400)

    mark_all = body.get('mark_all', False)

    if mark_all:
        Notification.objects.filter(
            recipient_school_id=student_id,
            is_read=False
        ).update(is_read=True)
        return json_response({
            'success': True,
            'message': 'All notifications marked as read'
        }, 200)
    else:
        notification_id = body.get('notification_id', '').strip()
        if not notification_id:
            return error_response('notification_id or mark_all is required', 400)

        try:
            notification = Notification.objects.get(
                notification_id=notification_id,
                recipient_school_id=student_id
            )
            notification.is_read = True
            notification.save()
            return json_response({
                'success': True
            }, 200)
        except Notification.DoesNotExist:
            return error_response('Notification not found', 404)
