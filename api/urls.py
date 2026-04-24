from django.urls import path
from api import auth, books, transactions, registration, notifications, user_portal, views

urlpatterns = [
    path('ping', views.ping, name='ping'),
    
    path('login', auth.login, name='login'),
    path('logout', auth.logout, name='logout'),
    
    path('register_request', registration.register_request, name='register_request'),
    path('register_student', registration.register_student, name='register_student'),
    path('admin/registration-requests', registration.get_registration_requests, name='get_registration_requests'),
    path('admin/registration-requests/<str:request_id>/decision', registration.registration_decision, name='registration_decision'),
    
    path('books', books.get_books, name='get_books'),
    path('books/search', books.search_books, name='search_books'),
    path('books/search/suggest', books.search_suggest, name='search_suggest'),
    path('books/categories', books.get_book_categories, name='get_book_categories'),
    path('categories', books.get_categories, name='get_categories'),
    path('admin/books/check-no', books.check_book_no, name='check_book_no'),
    path('admin/books/add', books.add_book, name='add_book'),
    path('admin/books/bulk', books.bulk_add_books, name='bulk_add_books'),
    path('admin/books/update', books.update_book, name='update_book'),
    path('admin/books/delete', books.delete_book, name='delete_book'),
    path('admin/categories/create', views.create_category, name='create_category'),
    path('admin/categories/rename', views.rename_category, name='rename_category'),
    path('admin/categories/delete', views.delete_category, name='delete_category'),
    
    path('reserve', transactions.reserve_book, name='reserve_book'),
    path('admin/reservations/approve', transactions.approve_reservation, name='approve_reservation'),
    path('admin/reservations/deny', transactions.deny_reservation, name='deny_reservation'),
    path('admin/reservations/activate-borrow', transactions.activate_borrow, name='activate_borrow'),
    path('admin/reservations/return', transactions.return_book, name='return_book'),
    path('admin/reservations/cancel', transactions.cancel_transaction, name='cancel_transaction'),
    
    path('my/notifications', notifications.get_notifications, name='get_notifications'),
    path('my/notifications/read', notifications.mark_notification_read, name='mark_notification_read'),
    
    path('my/transactions', user_portal.get_my_transactions, name='get_my_transactions'),
    path('my/profile', user_portal.get_my_profile, name='get_my_profile'),
    path('my/profile/update-photo', user_portal.update_profile_photo, name='update_profile_photo'),
    
    path('admin/users', views.get_users, name='get_users'),
    path('admin/users/summary', views.get_users_summary, name='get_users_summary'),
    path('admin/users/renew', views.renew_account, name='renew_account'),
    
    path('courses', views.get_courses, name='get_courses'),
]
