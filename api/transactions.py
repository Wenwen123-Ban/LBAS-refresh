import json
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.utils import timezone
from datetime import timedelta

from core.models import Transaction, Book, UserProfile
from api.utils import (
    parse_json_body, require_auth, require_admin, error_response, json_response,
    calculate_deadline, create_notification, sync_book_transactions
)
from api.expiry import run_expiry_check


@require_http_methods(['POST'])
def reserve_book(request):
    """
    POST /api/reserve
    Auth: student required
    Body: { book_no, reservation_note, pickup_location }
    """
    student_id = require_auth(request)
    if not student_id:
        return error_response('Authentication required', 401)

    try:
        student = UserProfile.objects.get(school_id=student_id)
    except UserProfile.DoesNotExist:
        return error_response('Student not found', 404)

    if student.account_status_detail == 'expired':
        return error_response('Your account has expired', 403)

    body = parse_json_body(request)
    if not body:
        return error_response('Invalid JSON', 400)

    book_no = body.get('book_no', '').strip()
    reservation_note = body.get('reservation_note', '').strip()
    pickup_location = body.get('pickup_location', '').strip()

    if not book_no:
        return error_response('book_no is required', 400)

    try:
        book = Book.objects.get(book_no=book_no)
    except Book.DoesNotExist:
        return error_response('Book not found', 404)

    active_transaction = Transaction.objects.filter(
        student_id=student_id,
        book_no=book_no,
        status__in=['Pending', 'Reserved', 'Borrowed']
    ).first()

    if active_transaction:
        return error_response('You already have an active transaction for this book', 409)

    active_count = Transaction.objects.filter(
        student_id=student_id,
        status__in=['Pending', 'Reserved']
    ).count()

    if active_count >= 5:
        return error_response('You have reached the maximum number of active reservations (5)', 403)

    queue_position = Transaction.objects.filter(
        book_no=book_no,
        status__in=['Pending', 'Reserved', 'Borrowed']
    ).count() + 1

    now = timezone.now()
    pending_expires_at = now + timedelta(hours=24)

    transaction = Transaction.objects.create(
        book_no=book_no,
        book_title=book.title,
        student_id=student_id,
        student_name=student.name,
        status='Pending',
        is_approved=False,
        reservation_note=reservation_note,
        pickup_location=pickup_location,
        queue_position=queue_position,
        pending_expires_at=pending_expires_at
    )

    if book.status == 'Available':
        book.status = 'Pending'
        book.save()

    sync_book_transactions(book_no)

    return json_response({
        'transaction_id': str(transaction.transaction_id),
        'queue_position': queue_position,
        'pending_expires_at': pending_expires_at.isoformat()
    }, 201)


@require_http_methods(['POST'])
def approve_reservation(request):
    """
    POST /api/admin/reservations/approve
    Auth: admin required
    Body: { transaction_id, pickup_window_value, pickup_window_unit }
    """
    admin_school_id = require_admin(request)
    if not admin_school_id:
        return error_response('Admin authentication required', 401)

    body = parse_json_body(request)
    if not body:
        return error_response('Invalid JSON', 400)

    transaction_id = body.get('transaction_id', '').strip()
    pickup_window_value = body.get('pickup_window_value')
    pickup_window_unit = body.get('pickup_window_unit', '').strip()

    if not transaction_id or pickup_window_value is None or not pickup_window_unit:
        return error_response('transaction_id, pickup_window_value, and pickup_window_unit are required', 400)

    try:
        transaction = Transaction.objects.get(transaction_id=transaction_id)
    except Transaction.DoesNotExist:
        return error_response('Transaction not found', 404)

    if transaction.status != 'Pending':
        return error_response('Transaction is not in Pending status', 400)

    try:
        admin = UserProfile.objects.get(school_id=admin_school_id)
    except UserProfile.DoesNotExist:
        return error_response('Admin not found', 404)

    pickup_deadline = calculate_deadline(pickup_window_value, pickup_window_unit)

    transaction.status = 'Reserved'
    transaction.is_approved = True
    transaction.approved_by = admin_school_id
    transaction.approved_by_name = admin.name
    transaction.date_approved = timezone.now()
    transaction.pickup_deadline = pickup_deadline
    transaction.save()

    book = Book.objects.get(book_no=transaction.book_no)
    if book.status == 'Pending':
        book.status = 'Reserved'
        book.save()

    create_notification(
        recipient_school_id=transaction.student_id,
        notification_type='reservation_approved',
        title='Reservation Approved',
        message=f'Your reservation for "{transaction.book_title}" was approved by {admin.name}. Pick up by {pickup_deadline.strftime("%Y-%m-%d %H:%M")}.',
        related_transaction_id=transaction.transaction_id,
        related_book_no=transaction.book_no,
        sent_by=admin_school_id
    )

    return json_response({
        'success': True,
        'pickup_deadline': pickup_deadline.isoformat()
    }, 200)


@require_http_methods(['POST'])
def deny_reservation(request):
    """
    POST /api/admin/reservations/deny
    Auth: admin required
    Body: { transaction_id, reason }
    """
    admin_school_id = require_admin(request)
    if not admin_school_id:
        return error_response('Admin authentication required', 401)

    body = parse_json_body(request)
    if not body:
        return error_response('Invalid JSON', 400)

    transaction_id = body.get('transaction_id', '').strip()
    reason = body.get('reason', '').strip()

    if not transaction_id:
        return error_response('transaction_id is required', 400)

    try:
        transaction = Transaction.objects.get(transaction_id=transaction_id)
    except Transaction.DoesNotExist:
        return error_response('Transaction not found', 404)

    transaction.status = 'Cancelled'
    transaction.save()

    sync_book_transactions(transaction.book_no)

    create_notification(
        recipient_school_id=transaction.student_id,
        notification_type='reservation_expired',
        title='Reservation Denied',
        message=f'Your reservation for "{transaction.book_title}" was denied. Reason: {reason}',
        related_transaction_id=transaction.transaction_id,
        related_book_no=transaction.book_no,
        sent_by=admin_school_id
    )

    return json_response({
        'success': True
    }, 200)


@require_http_methods(['POST'])
def activate_borrow(request):
    """
    POST /api/admin/reservations/activate-borrow
    Auth: admin required
    Body: { transaction_id, return_window_value, return_window_unit }
    """
    admin_school_id = require_admin(request)
    if not admin_school_id:
        return error_response('Admin authentication required', 401)

    body = parse_json_body(request)
    if not body:
        return error_response('Invalid JSON', 400)

    transaction_id = body.get('transaction_id', '').strip()
    return_window_value = body.get('return_window_value')
    return_window_unit = body.get('return_window_unit', '').strip()

    if not transaction_id or return_window_value is None or not return_window_unit:
        return error_response('transaction_id, return_window_value, and return_window_unit are required', 400)

    try:
        transaction = Transaction.objects.get(transaction_id=transaction_id)
    except Transaction.DoesNotExist:
        return error_response('Transaction not found', 404)

    if transaction.status != 'Reserved' or not transaction.is_approved:
        return error_response('Transaction is not in Reserved status or not approved', 400)

    try:
        admin = UserProfile.objects.get(school_id=admin_school_id)
    except UserProfile.DoesNotExist:
        return error_response('Admin not found', 404)

    return_due_date = calculate_deadline(return_window_value, return_window_unit)

    transaction.status = 'Borrowed'
    transaction.date_borrowed = timezone.now()
    transaction.return_due_date = return_due_date
    transaction.save()

    book = Book.objects.get(book_no=transaction.book_no)
    book.status = 'Borrowed'
    book.save()

    create_notification(
        recipient_school_id=transaction.student_id,
        notification_type='borrow_activated',
        title='Book Borrowed',
        message=f'You borrowed "{transaction.book_title}" approved by {admin.name}. Return by {return_due_date.strftime("%Y-%m-%d %H:%M")}.',
        related_transaction_id=transaction.transaction_id,
        related_book_no=transaction.book_no,
        sent_by=admin_school_id
    )

    return json_response({
        'success': True,
        'return_due_date': return_due_date.isoformat()
    }, 200)


@require_http_methods(['POST'])
def return_book(request):
    """
    POST /api/admin/reservations/return
    Auth: admin required
    Body: { transaction_id }
    """
    admin_school_id = require_admin(request)
    if not admin_school_id:
        return error_response('Admin authentication required', 401)

    body = parse_json_body(request)
    if not body:
        return error_response('Invalid JSON', 400)

    transaction_id = body.get('transaction_id', '').strip()
    if not transaction_id:
        return error_response('transaction_id is required', 400)

    try:
        transaction = Transaction.objects.get(transaction_id=transaction_id)
    except Transaction.DoesNotExist:
        return error_response('Transaction not found', 404)

    transaction.status = 'Returned'
    transaction.date_returned = timezone.now()
    transaction.save()

    sync_book_transactions(transaction.book_no)

    return json_response({
        'success': True
    }, 200)


@require_http_methods(['POST'])
def cancel_transaction(request):
    """
    POST /api/admin/reservations/cancel
    Auth: admin required
    Body: { transaction_id }
    """
    admin_school_id = require_admin(request)
    if not admin_school_id:
        return error_response('Admin authentication required', 401)

    body = parse_json_body(request)
    if not body:
        return error_response('Invalid JSON', 400)

    transaction_id = body.get('transaction_id', '').strip()
    if not transaction_id:
        return error_response('transaction_id is required', 400)

    try:
        transaction = Transaction.objects.get(transaction_id=transaction_id)
    except Transaction.DoesNotExist:
        return error_response('Transaction not found', 404)

    transaction.status = 'Cancelled'
    transaction.save()

    sync_book_transactions(transaction.book_no)

    return json_response({
        'success': True
    }, 200)
