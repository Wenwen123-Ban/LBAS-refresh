const API_BASE = '/api';
const ITEMS_PER_PAGE = 30;
const PORTAL_ROUTES = {
    admin: '/admin-portal/',
    student: '/student-portal/'
};

let currentPage = 1;
let currentCategory = 'all';
let currentSort = 'random';
let currentSearchQuery = '';
let selectedBook = null;
let studentToken = localStorage.getItem('studentToken');
let adminToken = localStorage.getItem('adminToken');

document.addEventListener('DOMContentLoaded', () => {
    initializeEventListeners();
    loadCategories();
    loadBooks();
});

function initializeEventListeners() {
    document.getElementById('loginBtn').addEventListener('click', openLoginModal);
    document.getElementById('loginForm').addEventListener('submit', handleLogin);
    document.querySelector('.modal-close').addEventListener('click', closeLoginModal);
    document.getElementById('isAdmin').addEventListener('change', togglePasswordField);
    document.getElementById('searchInput').addEventListener('input', debounce(handleSearch, 500));
    document.getElementById('categoryFilter').addEventListener('change', handleCategoryChange);
    document.getElementById('sortFilter').addEventListener('change', handleSortChange);
}

function togglePasswordField() {
    const isAdmin = document.getElementById('isAdmin').checked;
    const passwordGroup = document.getElementById('passwordGroup');
    const passwordInput = document.getElementById('password');
    
    if (isAdmin) {
        passwordGroup.style.display = 'flex';
        passwordInput.required = true;
    } else {
        passwordGroup.style.display = 'none';
        passwordInput.required = false;
        passwordInput.value = '';
    }
}

function debounce(func, delay) {
    let timeoutId;
    return function(...args) {
        clearTimeout(timeoutId);
        timeoutId = setTimeout(() => func.apply(this, args), delay);
    };
}

function handleSearch(e) {
    const query = e.target.value.trim();
    currentSearchQuery = query;
    currentPage = 1;
    
    if (query.length > 0) {
        searchBooks(query);
    } else {
        loadBooks();
    }
}

function handleCategoryChange(e) {
    currentCategory = e.target.value;
    currentPage = 1;
    loadBooks();
}

function handleSortChange(e) {
    currentSort = e.target.value;
    currentPage = 1;
    loadBooks();
}

function loadCategories() {
    fetch(`${API_BASE}/categories`)
        .then(res => res.json())
        .then(data => {
            const categoryFilter = document.getElementById('categoryFilter');
            categoryFilter.innerHTML = '<option value="all">All Categories</option>';
            
            if (data.categories) {
                data.categories.forEach(category => {
                    if (category !== 'All') {
                        const option = document.createElement('option');
                        option.value = category;
                        option.textContent = category;
                        categoryFilter.appendChild(option);
                    }
                });
            }
        })
        .catch(error => console.error('Error loading categories:', error));
}

function loadBooks() {
    const bookGrid = document.getElementById('bookGrid');
    bookGrid.innerHTML = getSkeletonLoading(12);
    
    const params = new URLSearchParams({
        page: currentPage,
        limit: ITEMS_PER_PAGE,
        sort: currentSort,
        category: currentCategory
    });
    
    fetch(`${API_BASE}/books?${params}`)
        .then(res => res.json())
        .then(data => {
            renderBooks(data.data || []);
            renderPagination(data.pagination || {});
        })
        .catch(error => {
            console.error('Error loading books:', error);
            bookGrid.innerHTML = getErrorState('Failed to load books. Please try again.');
        });
}

function searchBooks(query) {
    const bookGrid = document.getElementById('bookGrid');
    bookGrid.innerHTML = getSkeletonLoading(12);
    
    const params = new URLSearchParams({
        q: query,
        page: currentPage,
        limit: ITEMS_PER_PAGE,
        sort: currentSort,
        category: currentCategory
    });
    
    fetch(`${API_BASE}/books/search?${params}`)
        .then(res => res.json())
        .then(data => {
            if (data.data && data.data.length > 0) {
                renderBooks(data.data);
                renderPagination(data.pagination || {});
            } else {
                bookGrid.innerHTML = getEmptyState('📚', 'No books found matching your search.');
            }
        })
        .catch(error => {
            console.error('Error searching books:', error);
            bookGrid.innerHTML = getErrorState('Search failed. Please try again.');
        });
}

function renderBooks(books) {
    const bookGrid = document.getElementById('bookGrid');
    
    if (books.length === 0) {
        bookGrid.innerHTML = getEmptyState('📚', 'No books available.');
        return;
    }
    
    bookGrid.innerHTML = books.map(book => `
        <div class="book-card" onclick="openBookDetail('${book.book_no}')">
            <img src="${book.cover_image || '/static/images/default_book.svg'}" alt="${book.title}" class="book-cover">
            <div class="book-info">
                <h3 class="book-title">${escapeHtml(book.title)}</h3>
                <p class="book-author">${escapeHtml(book.author || 'Unknown')}</p>
                <span class="book-status ${book.status.toLowerCase()}">${book.status}</span>
            </div>
        </div>
    `).join('');
}

function renderPagination(pagination) {
    const container = document.getElementById('paginationContainer');
    
    if (!pagination.total_pages || pagination.total_pages <= 1) {
        container.innerHTML = '';
        return;
    }
    
    let html = '';
    
    if (pagination.has_prev) {
        html += `<button class="pagination-btn" onclick="goToPage(${pagination.page - 1})">← Prev</button>`;
    }
    
    for (let i = 1; i <= pagination.total_pages; i++) {
        if (i === pagination.page) {
            html += `<button class="pagination-btn active">${i}</button>`;
        } else if (i <= 3 || i > pagination.total_pages - 3 || Math.abs(i - pagination.page) <= 1) {
            html += `<button class="pagination-btn" onclick="goToPage(${i})">${i}</button>`;
        } else if (i === 4 || i === pagination.total_pages - 3) {
            html += `<span class="pagination-btn" style="cursor: default; border: none; background: transparent;">...</span>`;
        }
    }
    
    if (pagination.has_next) {
        html += `<button class="pagination-btn" onclick="goToPage(${pagination.page + 1})">Next →</button>`;
    }
    
    container.innerHTML = html;
}

function goToPage(page) {
    currentPage = page;
    window.scrollTo({ top: 0, behavior: 'smooth' });
    
    if (currentSearchQuery.length > 0) {
        searchBooks(currentSearchQuery);
    } else {
        loadBooks();
    }
}

function openBookDetail(bookNo) {
    selectedBook = bookNo;
    const panel = document.getElementById('bookDetailPanel');
    panel.classList.add('open');
    document.body.querySelector('.books-container').classList.add('panel-open');
    loadBookDetail(bookNo);
}

function closeBookDetail() {
    const panel = document.getElementById('bookDetailPanel');
    panel.classList.remove('open');
    document.body.querySelector('.books-container').classList.remove('panel-open');
    selectedBook = null;
}

function loadBookDetail(bookNo) {
    const panel = document.getElementById('bookDetailPanel');
    
    panel.innerHTML = `
        <div class="panel-header">
            <h3>Book Details</h3>
            <button class="panel-close" onclick="closeBookDetail()">×</button>
        </div>
        <div class="panel-content" style="padding: 20px;">
            <div class="loading-skeleton" style="width: 100%; height: 300px; border-radius: 8px; margin-bottom: 20px;"></div>
            <div class="loading-skeleton" style="width: 100%; height: 20px; margin-bottom: 10px;"></div>
            <div class="loading-skeleton" style="width: 80%; height: 16px; margin-bottom: 20px;"></div>
        </div>
    `;
    
    fetch(`${API_BASE}/books/${bookNo}`)
        .then(res => {
            if (!res.ok) throw new Error('Book not found');
            return res.json();
        })
        .then(book => {
            renderBookDetailPanel(book);
        })
        .catch(error => {
            console.error('Error loading book detail:', error);
            panel.innerHTML = `
                <div class="panel-header">
                    <h3>Book Details</h3>
                    <button class="panel-close" onclick="closeBookDetail()">×</button>
                </div>
                <div class="panel-content">
                    ${getErrorState('Failed to load book details.')}
                </div>
            `;
        });
}

function renderBookDetailPanel(book) {
    const panel = document.getElementById('bookDetailPanel');
    const coverUrl = book.cover_image || '/static/images/default_book.svg';
    
    const queueCount = book.queue_count || 0;
    const addedDate = new Date(book.added_at).toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'long',
        day: 'numeric'
    });
    
    const reserveButtonText = getReserveButtonText(book);
    const isLoggedIn = !!studentToken;
    const isExpired = localStorage.getItem('accountStatus') === 'expired';
    
    let ratingHtml = '';
    if (isLoggedIn && !isExpired) {
        ratingHtml = `
            <div class="rating-input" id="ratingInput">
                ${[1, 2, 3, 4, 5].map(i => `<span class="rating-star" onclick="submitRating(${i})">★</span>`).join('')}
            </div>
            <div class="rating-tooltip">Click to rate this book</div>
        `;
    } else if (!isLoggedIn) {
        ratingHtml = `
            <div class="rating-tooltip">Log in to rate</div>
        `;
    } else {
        ratingHtml = `
            <div class="rating-tooltip">Your account has expired</div>
        `;
    }
    
    let reserveButtonHtml = '';
    if (!isLoggedIn) {
        reserveButtonHtml = `<button class="reserve-button" onclick="openLoginModal()">Log in to Reserve</button>`;
    } else if (isExpired) {
        reserveButtonHtml = `<button class="reserve-button" disabled>Account Expired</button>`;
    } else {
        reserveButtonHtml = `<button class="reserve-button" onclick="showReserveForm('${book.book_no}')">${reserveButtonText}</button>`;
    }
    
    panel.innerHTML = `
        <div class="panel-header">
            <h3>Book Details</h3>
            <button class="panel-close" onclick="closeBookDetail()">×</button>
        </div>
        <div class="panel-content">
            <img src="${coverUrl}" alt="${escapeHtml(book.title)}" class="book-cover-large">
            
            <h2 class="book-title-large">${escapeHtml(book.title)}</h2>
            <p class="book-author-large">${escapeHtml(book.author || 'Unknown Author')}</p>
            
            <span class="book-category-badge">${escapeHtml(book.category)}</span>
            <span class="book-status ${book.status.toLowerCase()}" style="display: inline-block; margin-left: 8px;">${book.status}</span>
            
            <div class="divider"></div>
            
            <div class="rating-section">
                <div class="rating-display">
                    <span class="stars">${book.average_rating || 0}★</span>
                    <span class="rating-count">${book.rating_count || 0} ratings</span>
                </div>
                ${ratingHtml}
            </div>
            
            <div class="divider"></div>
            
            <div class="queue-info">
                📊 <strong>${queueCount}</strong> student${queueCount !== 1 ? 's' : ''} in queue
            </div>
            
            <div class="added-info">
                📅 Added on ${addedDate}
            </div>
            
            <div class="divider"></div>
            
            ${reserveButtonHtml}
        </div>
    `;
}

function getReserveButtonText(book) {
    if (book.user_pending) return 'Reservation Pending';
    if (book.user_reserved) return 'Already Reserved';
    if (book.status === 'Available') return 'Reserve This Book';
    return `Join Queue (#${book.queue_position || 1})`;
}

function showReserveForm(bookNo) {
    const panel = document.getElementById('bookDetailPanel');
    const panelContent = panel.querySelector('.panel-content');
    
    panelContent.innerHTML = `
        <form class="reserve-form" onsubmit="submitReservation(event, '${bookNo}')">
            <h3 style="color: var(--text-light); margin: 0 0 20px 0; font-size: 1.2rem;">Reserve Book</h3>
            
            <div class="form-group">
                <label for="reservationNote">Reservation Note (Optional)</label>
                <textarea id="reservationNote" placeholder="Any note for the librarian?" style="min-height: 80px;"></textarea>
            </div>
            
            <div class="form-group">
                <label for="pickupLocation">Preferred Pickup Location (Optional)</label>
                <input type="text" id="pickupLocation" placeholder="e.g., Main Library, Room 101">
            </div>
            
            <div style="display: flex; gap: 10px; margin-top: 20px;">
                <button type="button" class="reserve-button" onclick="openBookDetail('${bookNo}')" style="background: var(--muted);">← Back</button>
                <button type="submit" class="reserve-button success">✓ Confirm Reserve</button>
            </div>
            
            <div id="reserveError" class="error-message" style="display: none; margin-top: 16px;"></div>
        </form>
    `;
}

function submitReservation(event, bookNo) {
    event.preventDefault();
    
    const reservationNote = document.getElementById('reservationNote').value.trim();
    const pickupLocation = document.getElementById('pickupLocation').value.trim();
    
    if (!studentToken) {
        openLoginModal();
        return;
    }
    
    const submitBtn = event.target.querySelector('button[type="submit"]');
    const errorDiv = document.getElementById('reserveError');
    submitBtn.disabled = true;
    errorDiv.style.display = 'none';
    
    fetch(`${API_BASE}/reserve`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${studentToken}`
        },
        body: JSON.stringify({
            book_no: bookNo,
            reservation_note: reservationNote,
            pickup_location: pickupLocation
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            errorDiv.textContent = data.error;
            errorDiv.style.display = 'block';
            submitBtn.disabled = false;
        } else {
            showReservationSuccess(data.queue_position);
        }
    })
    .catch(error => {
        console.error('Error submitting reservation:', error);
        errorDiv.textContent = 'Failed to submit reservation. Please try again.';
        errorDiv.style.display = 'block';
        submitBtn.disabled = false;
    });
}

function showReservationSuccess(queuePosition) {
    const panel = document.getElementById('bookDetailPanel');
    const panelContent = panel.querySelector('.panel-content');
    
    panelContent.innerHTML = `
        <div style="text-align: center; padding: 40px 20px;">
            <div style="font-size: 4rem; margin-bottom: 20px; animation: scaleIn 0.4s ease;">✓</div>
            <h2 style="color: var(--success); margin: 0 0 12px 0; font-size: 1.4rem;">Reservation Submitted!</h2>
            <p style="color: rgba(247, 249, 255, 0.8); margin: 0 0 20px 0; font-size: 0.95rem;">
                The librarian will review your reservation request.
            </p>
            <div style="background: rgba(56, 189, 248, 0.1); border: 1px solid rgba(56, 189, 248, 0.3); border-radius: 8px; padding: 16px; margin-top: 20px;">
                <p style="margin: 0; color: var(--accent); font-weight: 600;">Your queue position: <strong>#${queuePosition}</strong></p>
            </div>
        </div>
    `;
    
    setTimeout(() => {
        closeBookDetail();
    }, 3000);
}

function submitRating(stars) {
    if (!studentToken) {
        openLoginModal();
        return;
    }
    
    console.log(`Rating submitted: ${stars} stars for book ${selectedBook}`);
}

function openLoginModal() {
    document.getElementById('loginModal').style.display = 'flex';
}

function closeLoginModal() {
    document.getElementById('loginModal').style.display = 'none';
    document.getElementById('loginError').style.display = 'none';
}

function showPortalNavigationError(errorDiv, submitBtn) {
    errorDiv.textContent = 'Login succeeded, but the portal page is unavailable right now. Please try again or contact support.';
    errorDiv.style.display = 'block';
    submitBtn.disabled = false;
    submitBtn.textContent = 'Login';
}

function navigateToPortal(portalType, errorDiv, submitBtn) {
    const targetPath = PORTAL_ROUTES[portalType];

    if (!targetPath) {
        console.error(`Unknown portal type: ${portalType}`);
        showPortalNavigationError(errorDiv, submitBtn);
        return;
    }

    fetch(targetPath, { method: 'HEAD', cache: 'no-store' })
        .then(response => {
            if (!response.ok) {
                throw new Error(`Portal route check failed with status ${response.status}`);
            }

            window.location.assign(targetPath);
        })
        .catch(error => {
            console.error('Portal navigation failed:', error);
            showPortalNavigationError(errorDiv, submitBtn);
        });
}

function handleLogin(event) {
    event.preventDefault();
    
    const schoolId = document.getElementById('schoolId').value.trim();
    const password = document.getElementById('password').value;
    const isAdminChecked = document.getElementById('isAdmin').checked;
    const errorDiv = document.getElementById('loginError');
    const submitBtn = event.target.querySelector('button[type="submit"]');
    
    errorDiv.style.display = 'none';
    submitBtn.disabled = true;
    submitBtn.textContent = 'Logging in...';
    
    fetch(`${API_BASE}/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            school_id: schoolId,
            password: password,
            id_only: !isAdminChecked
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            errorDiv.textContent = data.error;
            errorDiv.style.display = 'block';
            submitBtn.disabled = false;
            submitBtn.textContent = 'Login';
        } else {
            const isAdminAccount = !!(data.profile && data.profile.is_staff);

            if (isAdminAccount) {
                localStorage.removeItem('studentToken');
                localStorage.removeItem('studentProfile');
                localStorage.setItem('adminToken', data.token);
                localStorage.setItem('adminProfile', JSON.stringify(data.profile));
                navigateToPortal('admin', errorDiv, submitBtn);
            } else {
                localStorage.removeItem('adminToken');
                localStorage.removeItem('adminProfile');
                localStorage.setItem('studentToken', data.token);
                localStorage.setItem('studentProfile', JSON.stringify(data.profile));
                localStorage.setItem('accountStatus', data.profile.account_status_detail || 'active');
                navigateToPortal('student', errorDiv, submitBtn);
            }
        }
    })
    .catch(error => {
        console.error('Login error:', error);
        errorDiv.textContent = 'Login failed. Please try again.';
        errorDiv.style.display = 'block';
        submitBtn.disabled = false;
        submitBtn.textContent = 'Login';
    });
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function getSkeletonLoading(count) {
    return Array(count).fill().map(() => `
        <div class="book-card" style="pointer-events: none;">
            <div class="book-cover loading-skeleton" style="height: 220px;"></div>
            <div class="book-info">
                <div class="loading-skeleton" style="height: 14px; margin-bottom: 8px;"></div>
                <div class="loading-skeleton" style="height: 12px; margin-bottom: 8px; width: 70%;"></div>
                <div class="loading-skeleton" style="height: 20px; width: 40%;"></div>
            </div>
        </div>
    `).join('');
}

function getErrorState(message) {
    return `
        <div class="empty-state">
            <div class="empty-state-icon">⚠️</div>
            <p>${message}</p>
        </div>
    `;
}

function getEmptyState(icon, message) {
    return `
        <div class="empty-state">
            <div class="empty-state-icon">${icon}</div>
            <p>${message}</p>
        </div>
    `;
}

window.addEventListener('click', (e) => {
    const modal = document.getElementById('loginModal');
    if (e.target === modal) {
        closeLoginModal();
    }
});
