from django.db import models
import uuid


class UserProfile(models.Model):
    CATEGORY_CHOICES = [
        ('College Student', 'College Student'),
        ('High School Student', 'High School Student'),
        ('Staff', 'Staff'),
    ]
    
    SCHOOL_LEVEL_CHOICES = [
        ('College', 'College'),
        ('High School', 'High School'),
    ]
    
    YEAR_LEVEL_CHOICES = [
        ('Grade 7', 'Grade 7'),
        ('Grade 8', 'Grade 8'),
        ('Grade 9', 'Grade 9'),
        ('Grade 10', 'Grade 10'),
        ('1st Year', '1st Year'),
        ('2nd Year', '2nd Year'),
        ('3rd Year', '3rd Year'),
        ('4th Year', '4th Year'),
    ]
    
    STATUS_CHOICES = [
        ('approved', 'Approved'),
        ('pending', 'Pending'),
        ('rejected', 'Rejected'),
        ('expired', 'Expired'),
    ]
    
    ACCOUNT_STATUS_CHOICES = [
        ('active', 'Active'),
        ('expiry_warned', 'Expiry Warned'),
        ('expired', 'Expired'),
    ]
    
    school_id = models.CharField(max_length=50, unique=True, primary_key=True)
    name = models.CharField(max_length=150)
    password = models.CharField(max_length=255)
    is_staff = models.BooleanField(default=False)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='approved')
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES)
    school_level = models.CharField(max_length=20, choices=SCHOOL_LEVEL_CHOICES)
    year_level = models.CharField(max_length=20, choices=YEAR_LEVEL_CHOICES)
    course = models.CharField(max_length=100, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    email = models.CharField(max_length=150, blank=True)
    photo = models.CharField(max_length=255, default='avatar_fox.svg')
    account_expires_at = models.DateTimeField(null=True, blank=True)
    expiry_notified = models.BooleanField(default=False)
    account_status_detail = models.CharField(max_length=30, choices=ACCOUNT_STATUS_CHOICES, default='active')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'lbas_users'

    def __str__(self):
        return f"{self.name} ({self.school_id})"


class Book(models.Model):
    STATUS_CHOICES = [
        ('Available', 'Available'),
        ('Pending', 'Pending'),
        ('Reserved', 'Reserved'),
        ('Borrowed', 'Borrowed'),
        ('Unreturned', 'Unreturned'),
    ]
    
    book_no = models.CharField(max_length=50, unique=True, primary_key=True)
    title = models.CharField(max_length=255)
    author = models.CharField(max_length=150, blank=True)
    category = models.CharField(max_length=80, default='General')
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='Available')
    cover_image = models.CharField(max_length=255, default='default_book.jpg')
    added_by = models.CharField(max_length=50, blank=True)
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'lbas_books'

    def __str__(self):
        return f"{self.title} ({self.book_no})"


class Transaction(models.Model):
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Reserved', 'Reserved'),
        ('Borrowed', 'Borrowed'),
        ('Returned', 'Returned'),
        ('Cancelled', 'Cancelled'),
        ('Expired', 'Expired'),
        ('Unavailable', 'Unavailable'),
        ('Unreturned', 'Unreturned'),
    ]
    
    transaction_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    book_no = models.CharField(max_length=50)
    book_title = models.CharField(max_length=255)
    student_id = models.CharField(max_length=50)
    student_name = models.CharField(max_length=150)
    status = models.CharField(max_length=30, choices=STATUS_CHOICES, default='Pending')
    date_reserved = models.DateTimeField(auto_now_add=True)
    is_approved = models.BooleanField(default=False)
    approved_by = models.CharField(max_length=50, blank=True)
    approved_by_name = models.CharField(max_length=150, blank=True)
    date_approved = models.DateTimeField(null=True, blank=True)
    pickup_deadline = models.DateTimeField(null=True, blank=True)
    pending_expires_at = models.DateTimeField(null=True, blank=True)
    date_borrowed = models.DateTimeField(null=True, blank=True)
    return_due_date = models.DateTimeField(null=True, blank=True)
    date_returned = models.DateTimeField(null=True, blank=True)
    reservation_note = models.TextField(blank=True)
    pickup_location = models.CharField(max_length=100, blank=True)
    queue_position = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'lbas_transactions'

    def __str__(self):
        return f"Transaction {self.transaction_id}: {self.book_title} by {self.student_name}"


class RegistrationRequest(models.Model):
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('approved', 'Approved'),
        ('rejected', 'Rejected'),
    ]
    
    request_id = models.CharField(max_length=100, unique=True, primary_key=True)
    request_number = models.CharField(max_length=10)
    name = models.CharField(max_length=150)
    school_id = models.CharField(max_length=50)
    password = models.CharField(max_length=255)
    year_level = models.CharField(max_length=20)
    school_level = models.CharField(max_length=20)
    category = models.CharField(max_length=50)
    course = models.CharField(max_length=100, blank=True)
    phone_number = models.CharField(max_length=20, blank=True)
    email = models.CharField(max_length=150, blank=True)
    photo = models.CharField(max_length=255, default='avatar_fox.svg')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    reviewed_by = models.CharField(max_length=50, blank=True)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    pending_expires_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'lbas_registration_requests'

    def __str__(self):
        return f"Registration Request {self.request_number}: {self.name}"


class Session(models.Model):
    token = models.CharField(max_length=100, unique=True, primary_key=True)
    school_id = models.CharField(max_length=50)
    is_staff = models.BooleanField(default=False)
    expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'lbas_sessions'

    def __str__(self):
        return f"Session {self.token[:10]}... for {self.school_id}"


class Notification(models.Model):
    NOTIFICATION_TYPE_CHOICES = [
        ('reservation_pending', 'Reservation Pending'),
        ('reservation_approved', 'Reservation Approved'),
        ('borrow_activated', 'Borrow Activated'),
        ('overdue_reminder', 'Overdue Reminder'),
        ('registration_approved', 'Registration Approved'),
        ('reservation_expired', 'Reservation Expired'),
        ('account_expiry_warning', 'Account Expiry Warning'),
        ('account_expired', 'Account Expired'),
    ]
    
    notification_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    recipient_school_id = models.CharField(max_length=50)
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPE_CHOICES)
    title = models.CharField(max_length=255)
    message = models.TextField()
    related_transaction_id = models.UUIDField(null=True, blank=True)
    related_book_no = models.CharField(max_length=50, blank=True)
    sent_by = models.CharField(max_length=50, blank=True)
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'lbas_notifications'

    def __str__(self):
        return f"Notification {self.notification_id}: {self.notification_type}"


class DateRestriction(models.Model):
    ACTION_CHOICES = [
        ('ban', 'Ban'),
        ('lift', 'Lift'),
    ]
    
    date = models.DateField(unique=True, primary_key=True)
    action = models.CharField(max_length=10, choices=ACTION_CHOICES)
    reason = models.TextField(blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'lbas_date_restrictions'

    def __str__(self):
        return f"DateRestriction {self.date}: {self.action}"


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True, primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'lbas_categories'

    def __str__(self):
        return self.name


class Course(models.Model):
    name = models.CharField(max_length=100, unique=True, primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'lbas_courses'

    def __str__(self):
        return self.name
