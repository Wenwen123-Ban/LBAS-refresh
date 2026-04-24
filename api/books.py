import json
from django.http import JsonResponse
from django.views.decorators.http import require_http_methods
from django.db.models import Q
import math
import os

from core.models import Book, Category
from api.utils import parse_json_body, require_admin, error_response, json_response, resolve_cover
from api.expiry import run_expiry_check


@require_http_methods(['GET'])
def check_book_no(request):
    """
    GET /api/admin/books/check-no
    Query param: book_no
    Returns: { available: True/False }
    """
    admin_school_id = require_admin(request)
    if not admin_school_id:
        return error_response('Admin authentication required', 401)

    book_no = request.GET.get('book_no', '').strip()
    if not book_no:
        return error_response('book_no is required', 400)

    available = not Book.objects.filter(book_no=book_no).exists()
    return json_response({'available': available}, 200)


@require_http_methods(['GET'])
def get_books(request):
    """
    GET /api/books
    Query params: category (optional), sort (random/az/za/newest), page, limit
    Returns paginated list of books with filtering and sorting.
    """
    run_expiry_check()

    category_filter = request.GET.get('category', 'all').strip()
    sort = request.GET.get('sort', 'random').strip()
    page = int(request.GET.get('page', 1))
    limit = min(int(request.GET.get('limit', 30)), 30)

    if page < 1:
        page = 1
    if limit < 1:
        limit = 30

    queryset = Book.objects.all()

    if category_filter and category_filter != 'all':
        queryset = queryset.filter(category=category_filter)

    if sort == 'az':
        queryset = queryset.order_by('title')
    elif sort == 'za':
        queryset = queryset.order_by('-title')
    elif sort == 'newest':
        queryset = queryset.order_by('-added_at')
    else:
        queryset = queryset.order_by('?')

    total = queryset.count()
    offset = (page - 1) * limit
    books = queryset[offset:offset + limit]

    books_list = []
    for book in books:
        books_list.append({
            'book_no': book.book_no,
            'title': book.title,
            'author': book.author,
            'category': book.category,
            'status': book.status,
            'cover_image': resolve_cover(book.cover_image),
            'added_by': book.added_by,
            'added_at': book.added_at.isoformat()
        })

    total_pages = math.ceil(total / limit) if limit > 0 else 0

    return json_response({
        'data': books_list,
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
def search_books(request):
    """
    GET /api/books/search
    Query params: q (required), category (optional), sort, page, limit
    Search algorithm: Priority 1 - title starts with, Priority 2 - title contains, Priority 3 - author contains
    """
    q = request.GET.get('q', '').strip()
    if not q or len(q) < 1:
        return error_response('q parameter required (minimum 1 character)', 400)

    category_filter = request.GET.get('category', '').strip()
    sort = request.GET.get('sort', 'random').strip()
    page = int(request.GET.get('page', 1))
    limit = min(int(request.GET.get('limit', 30)), 30)

    if page < 1:
        page = 1
    if limit < 1:
        limit = 30

    priority1 = Book.objects.filter(title__istartswith=q)
    priority2 = Book.objects.filter(title__icontains=q).exclude(title__istartswith=q)
    priority3 = Book.objects.filter(author__icontains=q).exclude(title__icontains=q)

    seen_ids = set(priority1.values_list('book_no', flat=True))
    priority2_filtered = [b for b in priority2 if b.book_no not in seen_ids]
    seen_ids.update([b.book_no for b in priority2_filtered])
    priority3_filtered = [b for b in priority3 if b.book_no not in seen_ids]

    combined = list(priority1) + priority2_filtered + priority3_filtered

    if category_filter and category_filter != 'all':
        combined = [b for b in combined if b.category == category_filter]

    if sort == 'az':
        combined.sort(key=lambda b: b.title)
    elif sort == 'za':
        combined.sort(key=lambda b: b.title, reverse=True)
    elif sort == 'newest':
        combined.sort(key=lambda b: b.added_at, reverse=True)

    total = len(combined)
    offset = (page - 1) * limit
    books = combined[offset:offset + limit]

    books_list = []
    for book in books:
        books_list.append({
            'book_no': book.book_no,
            'title': book.title,
            'author': book.author,
            'category': book.category,
            'status': book.status,
            'cover_image': resolve_cover(book.cover_image),
            'added_by': book.added_by,
            'added_at': book.added_at.isoformat()
        })

    total_pages = math.ceil(total / limit) if limit > 0 else 0

    return json_response({
        'data': books_list,
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
def search_suggest(request):
    """
    GET /api/books/search/suggest
    Query params: q (required)
    Returns top 8 suggestions: titles starting with q first, then titles containing q
    """
    q = request.GET.get('q', '').strip()
    if not q or len(q) < 1:
        return error_response('q parameter required (minimum 1 character)', 400)

    suggestions = []

    startswith = Book.objects.filter(title__istartswith=q).values_list('title', flat=True)[:8]
    suggestions.extend(list(startswith))

    if len(suggestions) < 8:
        contains = Book.objects.filter(
            title__icontains=q
        ).exclude(
            title__istartswith=q
        ).values_list('title', flat=True)[:8 - len(suggestions)]
        suggestions.extend(list(contains))

    return json_response({
        'suggestions': suggestions
    }, 200)


@require_http_methods(['POST'])
def add_book(request):
    """
    POST /api/admin/books/add
    Accepts: application/x-www-form-urlencoded or multipart/form-data
    Fields: book_no, title, author, category, cover_image (file, optional)
    """
    admin_school_id = require_admin(request)
    if not admin_school_id:
        return error_response('Admin authentication required', 401)

    book_no = request.POST.get('book_no', '').strip()
    title = request.POST.get('title', '').strip()
    author = request.POST.get('author', '').strip()
    category = request.POST.get('category', 'General').strip()
    cover_file = request.FILES.get('cover_image')

    if not book_no or not title:
        return error_response('book_no and title are required', 400)

    if Book.objects.filter(book_no=book_no).exists():
        return error_response('book_no already exists', 409)

    cover_image = 'default_book.jpg'

    if cover_file:
        allowed_extensions = ['jpg', 'jpeg', 'png', 'webp']
        file_ext = cover_file.name.split('.')[-1].lower()
        
        if file_ext not in allowed_extensions:
            return error_response('Only .jpg, .png, .webp files are allowed', 400)
        
        if cover_file.size > 2 * 1024 * 1024:
            return error_response('File size must be less than 2MB', 400)
        
        from django.conf import settings
        cover_dir = settings.BASE_DIR / 'static' / 'images' / 'covers'
        cover_dir.mkdir(parents=True, exist_ok=True)
        
        cover_filename = f"{book_no}.{file_ext}"
        cover_path = cover_dir / cover_filename
        
        with open(cover_path, 'wb') as f:
            for chunk in cover_file.chunks():
                f.write(chunk)
        
        cover_image = cover_filename

    book = Book.objects.create(
        book_no=book_no,
        title=title,
        author=author,
        category=category,
        status='Available',
        cover_image=cover_image,
        added_by=admin_school_id
    )

    return json_response({
        'success': True,
        'book': {
            'book_no': book.book_no,
            'title': book.title,
            'author': book.author,
            'category': book.category,
            'status': book.status,
            'cover_image': resolve_cover(book.cover_image),
            'added_by': book.added_by,
            'added_at': book.added_at.isoformat()
        }
    }, 201)


@require_http_methods(['POST'])
def bulk_add_books(request):
    """
    POST /api/admin/books/bulk
    Body: { lines, category }
    lines: "BOOK_NO | Title | Author\n..." format
    category: category for all books in the bulk
    """
    admin_school_id = require_admin(request)
    if not admin_school_id:
        return error_response('Admin authentication required', 401)

    body = parse_json_body(request)
    if not body:
        return error_response('Invalid JSON', 400)

    lines = body.get('lines', '').strip()
    category = body.get('category', 'General').strip()

    if not lines:
        return error_response('lines are required', 400)

    created = 0
    errors = []

    for i, line in enumerate(lines.split('\n'), 1):
        line = line.strip()
        if not line:
            continue

        parts = [p.strip() for p in line.split('|')]
        if len(parts) < 2:
            errors.append(f'Line {i}: Invalid format (expected BOOK_NO | Title | Author)')
            continue

        book_no = parts[0]
        title = parts[1]
        author = parts[2] if len(parts) > 2 else ''

        if not book_no or not title:
            errors.append(f'Line {i}: book_no and title are required')
            continue

        if Book.objects.filter(book_no=book_no).exists():
            errors.append(f'Line {i}: book_no {book_no} already exists')
            continue

        Book.objects.create(
            book_no=book_no,
            title=title,
            author=author,
            category=category,
            status='Available'
        )
        created += 1

    response_data = {
        'success': len(errors) == 0,
        'created': created,
        'total_lines': len(lines.split('\n'))
    }

    if errors:
        response_data['errors'] = errors

    return json_response(response_data, 200)


@require_http_methods(['POST'])
def update_book(request):
    """
    POST /api/admin/books/update
    Accepts: application/x-www-form-urlencoded or multipart/form-data
    Fields: book_no (identifier, cannot change), title, author, category, cover_image (file, optional)
    """
    admin_school_id = require_admin(request)
    if not admin_school_id:
        return error_response('Admin authentication required', 401)

    book_no = request.POST.get('book_no', '').strip()
    if not book_no:
        return error_response('book_no is required', 400)

    try:
        book = Book.objects.get(book_no=book_no)
    except Book.DoesNotExist:
        return error_response('Book not found', 404)

    if 'title' in request.POST:
        book.title = request.POST.get('title', '').strip()
    if 'author' in request.POST:
        book.author = request.POST.get('author', '').strip()
    if 'category' in request.POST:
        book.category = request.POST.get('category', '').strip()

    cover_file = request.FILES.get('cover_image')
    if cover_file:
        allowed_extensions = ['jpg', 'jpeg', 'png', 'webp']
        file_ext = cover_file.name.split('.')[-1].lower()
        
        if file_ext not in allowed_extensions:
            return error_response('Only .jpg, .png, .webp files are allowed', 400)
        
        if cover_file.size > 2 * 1024 * 1024:
            return error_response('File size must be less than 2MB', 400)
        
        from django.conf import settings
        cover_dir = settings.BASE_DIR / 'static' / 'images' / 'covers'
        cover_dir.mkdir(parents=True, exist_ok=True)
        
        old_cover = book.cover_image
        if old_cover and old_cover != 'default_book.jpg':
            old_path = cover_dir / old_cover
            if old_path.exists():
                old_path.unlink()
        
        cover_filename = f"{book_no}.{file_ext}"
        cover_path = cover_dir / cover_filename
        
        with open(cover_path, 'wb') as f:
            for chunk in cover_file.chunks():
                f.write(chunk)
        
        book.cover_image = cover_filename

    book.save()

    return json_response({
        'success': True,
        'book': {
            'book_no': book.book_no,
            'title': book.title,
            'author': book.author,
            'category': book.category,
            'status': book.status,
            'cover_image': resolve_cover(book.cover_image),
            'added_by': book.added_by,
            'added_at': book.added_at.isoformat()
        }
    }, 200)


@require_http_methods(['POST'])
def delete_book(request):
    """
    POST /api/admin/books/delete
    Body: { book_no }
    Delete book by book_no
    """
    admin_school_id = require_admin(request)
    if not admin_school_id:
        return error_response('Admin authentication required', 401)

    body = parse_json_body(request)
    if not body:
        return error_response('Invalid JSON', 400)

    book_no = body.get('book_no', '').strip()
    if not book_no:
        return error_response('book_no is required', 400)

    try:
        book = Book.objects.get(book_no=book_no)
        book.delete()
        return json_response({
            'success': True,
            'message': f'Book {book_no} deleted'
        }, 200)
    except Book.DoesNotExist:
        return error_response('Book not found', 404)


@require_http_methods(['GET'])
def get_categories(request):
    """
    GET /api/categories
    Public endpoint. Returns all category names as a simple list.
    "All" is always prepended as the first item.
    """
    categories = Category.objects.all().values_list('name', flat=True)
    categories_list = ['All'] + list(categories)

    return json_response({
        'categories': categories_list
    }, 200)


@require_http_methods(['GET'])
def get_book_categories(request):
    """
    GET /api/books/categories
    Returns all Category names
    """
    categories = Category.objects.all().values_list('name', flat=True)
    return json_response({
        'categories': list(categories)
    }, 200)
