from django.utils import timezone
from datetime import timedelta
from core.models import Transaction, UserProfile, Book, Notification
from api.utils import recalculate_book_status, create_notification


def run_expiry_check():
    """
    Run comprehensive expiry check for transactions and user accounts.
    This function is called by the management command and can also be
    called from other API endpoints.
    """
    now = timezone.now()
    affected_books = set()

    step1_books = handle_pending_expiry(now)
    affected_books.update(step1_books)

    step2_books = handle_reserved_expiry(now)
    affected_books.update(step2_books)

    step3_books = handle_borrowed_expiry(now)
    affected_books.update(step3_books)

    handle_account_expiry_warning(now)

    step5_books = handle_expired_accounts(now)
    affected_books.update(step5_books)

    for book_no in affected_books:
        recalculate_book_status(book_no)


def handle_pending_expiry(now):
    """
    Step 1: Cancel Pending transactions past pending_expires_at
    """
    affected_books = []
    expired_pending = Transaction.objects.filter(
        status='Pending',
        pending_expires_at__lt=now
    )

    for transaction in expired_pending:
        transaction.status = 'Cancelled'
        transaction.save()
        affected_books.append(transaction.book_no)

    return affected_books


def handle_reserved_expiry(now):
    """
    Step 2: Expire Reserved transactions past pickup_deadline
    """
    affected_books = []
    expired_reserved = Transaction.objects.filter(
        status='Reserved',
        pickup_deadline__lt=now
    )

    for transaction in expired_reserved:
        transaction.status = 'Expired'
        transaction.save()
        affected_books.append(transaction.book_no)

        create_notification(
            recipient_school_id=transaction.student_id,
            notification_type='reservation_expired',
            title='Reservation Expired',
            message=f'Your reservation for "{transaction.book_title}" has expired because you did not pick it up by the deadline.',
            related_transaction_id=transaction.transaction_id,
            related_book_no=transaction.book_no
        )

    return affected_books


def handle_borrowed_expiry(now):
    """
    Step 3: Flag Borrowed transactions past return_due_date as Unreturned
    """
    affected_books = []
    overdue_borrowed = Transaction.objects.filter(
        status='Borrowed',
        return_due_date__lt=now
    )

    for transaction in overdue_borrowed:
        transaction.status = 'Unreturned'
        transaction.save()
        affected_books.append(transaction.book_no)

        create_notification(
            recipient_school_id=transaction.student_id,
            notification_type='overdue_reminder',
            title='Book Overdue',
            message=f'Your borrowed book "{transaction.book_title}" is now overdue. Please return it immediately.',
            related_transaction_id=transaction.transaction_id,
            related_book_no=transaction.book_no
        )

    return affected_books


def handle_account_expiry_warning(now):
    """
    Step 4: Warn accounts expiring within 30 days
    """
    expiry_threshold = now + timedelta(days=30)

    expiring_soon = UserProfile.objects.filter(
        account_expires_at__lte=expiry_threshold,
        account_expires_at__gt=now,
        expiry_notified=False,
        is_staff=False
    )

    for user in expiring_soon:
        user.expiry_notified = True
        user.account_status_detail = 'expiry_warned'
        user.save()

        create_notification(
            recipient_school_id=user.school_id,
            notification_type='account_expiry_warning',
            title='Account Expiring Soon',
            message=f'Your library account expires on {user.account_expires_at.strftime("%Y-%m-%d")}. Contact the librarian to renew it.'
        )


def handle_expired_accounts(now):
    """
    Step 5: Expire accounts past their expiration date and cancel their transactions
    """
    affected_books = []

    expired_accounts = UserProfile.objects.filter(
        account_expires_at__lte=now,
        account_status_detail__in=['active', 'expiry_warned'],
        is_staff=False
    )

    for user in expired_accounts:
        user.status = 'expired'
        user.account_status_detail = 'expired'
        user.save()

        active_transactions = Transaction.objects.filter(
            student_id=user.school_id,
            status__in=['Pending', 'Reserved', 'Borrowed']
        )

        for transaction in active_transactions:
            transaction.status = 'Cancelled'
            transaction.save()
            affected_books.append(transaction.book_no)

        create_notification(
            recipient_school_id=user.school_id,
            notification_type='account_expired',
            title='Account Expired',
            message='Your library account has expired. You can no longer borrow books. Please contact the librarian.'
        )

    return affected_books
