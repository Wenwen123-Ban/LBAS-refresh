from django.contrib import admin

from core.models import (
    UserProfile, Book, Transaction, RegistrationRequest,
    Session, Notification, DateRestriction, Category, Course
)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ['school_id', 'name', 'status', 'is_staff', 'created_at']
    search_fields = ['school_id', 'name']


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ['book_no', 'title', 'author', 'category', 'status']
    search_fields = ['book_no', 'title', 'author']


@admin.register(Transaction)
class TransactionAdmin(admin.ModelAdmin):
    list_display = ['transaction_id', 'book_title', 'student_name', 'status', 'date_reserved']
    search_fields = ['student_id', 'book_no', 'book_title']


@admin.register(RegistrationRequest)
class RegistrationRequestAdmin(admin.ModelAdmin):
    list_display = ['request_number', 'name', 'school_id', 'status', 'created_at']
    search_fields = ['name', 'school_id']


@admin.register(Session)
class SessionAdmin(admin.ModelAdmin):
    list_display = ['token', 'school_id', 'is_staff', 'expires_at', 'created_at']
    search_fields = ['school_id', 'token']


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ['notification_id', 'recipient_school_id', 'notification_type', 'is_read', 'created_at']
    search_fields = ['recipient_school_id', 'notification_type']


@admin.register(DateRestriction)
class DateRestrictionAdmin(admin.ModelAdmin):
    list_display = ['date', 'action', 'reason']


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ['name', 'created_at']
