const API_BASE = '/api';
const CURRENT_DATE = new Date();

let adminToken = localStorage.getItem('adminToken');
let adminProfile = null;
let allBooks = [];
let selectedImageFile = null;
let selectedEditImageFile = null;
let availableCourses = [];

document.addEventListener('DOMContentLoaded', async () => {
    await verifyAccess();
    updateDate();
    loadAdminProfile();
    initializeEventListeners();
    loadBooks();
    loadCategories();
    loadCourses();
    initializeAddUserForm();
});

async function verifyAccess() {
    if (!adminToken) {
        window.location.href = '/';
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/my/profile`, {
            headers: { 'Authorization': `Bearer ${adminToken}` }
        });

        if (!response.ok) {
            localStorage.removeItem('adminToken');
            localStorage.removeItem('adminProfile');
            window.location.href = '/';
            return;
        }

        const data = await response.json();
        if (!data.is_staff) {
            localStorage.removeItem('adminToken');
            window.location.href = '/';
            return;
        }

        adminProfile = data;
        localStorage.setItem('adminProfile', JSON.stringify(data));
    } catch (error) {
        console.error('Verification error:', error);
        window.location.href = '/';
    }
}

function updateDate() {
    const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    const dateStr = CURRENT_DATE.toLocaleDateString('en-US', options);
    document.getElementById('currentDate').textContent = dateStr;
}

function loadAdminProfile() {
    if (!adminProfile) {
        adminProfile = JSON.parse(localStorage.getItem('adminProfile')) || {};
    }
    document.getElementById('adminSchoolId').textContent = adminProfile.school_id || '-';
}

function initializeEventListeners() {
    document.getElementById('bookNo').addEventListener('blur', validateBookNumber);
    document.getElementById('coverImage').addEventListener('change', handleImageSelection);
    document.getElementById('editCoverImage').addEventListener('change', handleEditImageSelection);
    document.getElementById('bookCategory').addEventListener('change', handleCategorySelection);
}

function initializeAddUserForm() {
    handleSchoolLevelChange();
    handleRoleChange();
}

function switchAdminPanel(panelName) {
    const panels = document.querySelectorAll('.content-panel');
    panels.forEach(p => p.classList.remove('active'));

    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(n => n.classList.remove('active'));

    let panelId, navItem;
    switch (panelName) {
        case 'books':
            panelId = 'booksPanel';
            navItem = document.querySelector('.nav-item:nth-child(1)');
            break;
        case 'users':
            panelId = 'usersPanel';
            navItem = document.querySelector('.nav-item:nth-child(2)');
            loadUsers();
            break;
        case 'reports':
            panelId = 'reportsPanel';
            navItem = document.querySelector('.nav-item:nth-child(3)');
            loadReports();
            break;
        case 'settings':
            panelId = 'settingsPanel';
            navItem = document.querySelector('.nav-item:nth-child(4)');
            break;
    }

    if (panelId) {
        document.getElementById(panelId).classList.add('active');
    }
    if (navItem) {
        navItem.classList.add('active');
    }
}

async function loadCategories() {
    try {
        const response = await fetch(`${API_BASE}/categories`);
        if (!response.ok) throw new Error('Failed to load categories');

        const data = await response.json();
        const categories = data.categories || [];

        const bookCategory = document.getElementById('bookCategory');
        const editBookCategory = document.getElementById('editBookCategory');

        bookCategory.innerHTML = '<option value="">Select category</option>';
        categories.forEach(cat => {
            if (cat !== 'All') {
                const option = document.createElement('option');
                option.value = cat;
                option.textContent = cat;
                bookCategory.appendChild(option);
            }
        });

        bookCategory.innerHTML += '<option value="__create__">+ Create new category</option>';

        editBookCategory.innerHTML = categories
            .filter(cat => cat !== 'All')
            .map(cat => `<option value="${cat}">${cat}</option>`)
            .join('');
    } catch (error) {
        console.error('Error loading categories:', error);
    }
}

function handleCategorySelection(e) {
    if (e.target.value === '__create__') {
        document.getElementById('createCategorySection').style.display = 'block';
        e.target.value = '';
    } else {
        document.getElementById('createCategorySection').style.display = 'none';
    }
}

function addNewCategory() {
    const categoryName = document.getElementById('newCategoryName').value.trim();
    if (!categoryName) {
        alert('Category name cannot be empty');
        return;
    }

    fetch(`${API_BASE}/admin/categories/create`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${adminToken}`
        },
        body: JSON.stringify({ category_name: categoryName })
    })
    .then(res => res.json())
    .then(data => {
        if (data.error) {
            alert('Error: ' + data.error);
        } else {
            document.getElementById('newCategoryName').value = '';
            document.getElementById('createCategorySection').style.display = 'none';
            loadCategories();
        }
    })
    .catch(error => console.error('Error adding category:', error));
}

async function validateBookNumber() {
    const bookNo = document.getElementById('bookNo').value.trim();
    const validationDiv = document.getElementById('bookNoValidation');

    if (!bookNo) {
        validationDiv.innerHTML = '';
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/admin/books/check-no?book_no=${encodeURIComponent(bookNo)}`);
        const data = await response.json();

        if (data.available) {
            validationDiv.innerHTML = '<span class="validation-valid">✓ Available</span>';
        } else {
            validationDiv.innerHTML = '<span class="validation-invalid">✗ Book number already exists</span>';
        }
    } catch (error) {
        console.error('Error validating book number:', error);
    }
}

function handleImageSelection(e) {
    const file = e.target.files[0];
    if (!file) {
        selectedImageFile = null;
        document.getElementById('imagePreview').style.display = 'none';
        return;
    }

    const validTypes = ['image/jpeg', 'image/png', 'image/webp'];
    if (!validTypes.includes(file.type)) {
        alert('Invalid file type. Only JPG, PNG, and WebP are allowed.');
        e.target.value = '';
        return;
    }

    if (file.size > 2 * 1024 * 1024) {
        alert('File size exceeds 2MB limit.');
        e.target.value = '';
        return;
    }

    selectedImageFile = file;
    const reader = new FileReader();
    reader.onload = (event) => {
        document.getElementById('previewImg').src = event.target.result;
        document.getElementById('imagePreview').style.display = 'block';
    };
    reader.readAsDataURL(file);
}

function handleEditImageSelection(e) {
    const file = e.target.files[0];
    if (!file) {
        selectedEditImageFile = null;
        return;
    }

    const validTypes = ['image/jpeg', 'image/png', 'image/webp'];
    if (!validTypes.includes(file.type)) {
        alert('Invalid file type. Only JPG, PNG, and WebP are allowed.');
        e.target.value = '';
        return;
    }

    if (file.size > 2 * 1024 * 1024) {
        alert('File size exceeds 2MB limit.');
        e.target.value = '';
        return;
    }

    selectedEditImageFile = file;
    const reader = new FileReader();
    reader.onload = (event) => {
        document.getElementById('editPreviewImg').src = event.target.result;
        document.getElementById('editImagePreview').style.display = 'block';
    };
    reader.readAsDataURL(file);
}

function clearImagePreview() {
    document.getElementById('coverImage').value = '';
    document.getElementById('imagePreview').style.display = 'none';
    selectedImageFile = null;
}

async function handleAddBook(event) {
    event.preventDefault();

    const bookNo = document.getElementById('bookNo').value.trim();
    const title = document.getElementById('bookTitle').value.trim();
    const author = document.getElementById('bookAuthor').value.trim();
    const category = document.getElementById('bookCategory').value;
    const errorDiv = document.getElementById('addBookError');
    const successDiv = document.getElementById('addBookSuccess');
    const submitBtn = event.target.querySelector('button[type="submit"]');

    errorDiv.style.display = 'none';
    successDiv.style.display = 'none';

    if (!bookNo || !title) {
        errorDiv.textContent = 'Book number and title are required';
        errorDiv.style.display = 'block';
        return;
    }

    try {
        const checkResponse = await fetch(`${API_BASE}/admin/books/check-no?book_no=${encodeURIComponent(bookNo)}`);
        const checkData = await checkResponse.json();

        if (!checkData.available) {
            errorDiv.textContent = 'This book number already exists';
            errorDiv.style.display = 'block';
            return;
        }

        const formData = new FormData();
        formData.append('book_no', bookNo);
        formData.append('title', title);
        if (author) formData.append('author', author);
        if (category) formData.append('category', category);
        if (selectedImageFile) formData.append('cover_image', selectedImageFile);

        submitBtn.disabled = true;
        submitBtn.textContent = 'Adding...';

        const response = await fetch(`${API_BASE}/admin/books/add`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${adminToken}`
            },
            body: formData
        });

        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || 'Failed to add book');
        }

        successDiv.textContent = `Book "${title}" added successfully!`;
        successDiv.style.display = 'block';

        event.target.reset();
        document.getElementById('imagePreview').style.display = 'none';
        selectedImageFile = null;
        loadBooks();

        setTimeout(() => {
            successDiv.style.display = 'none';
        }, 4000);
    } catch (error) {
        console.error('Error adding book:', error);
        errorDiv.textContent = error.message;
        errorDiv.style.display = 'block';
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = '➕ Add Book';
    }
}

async function loadBooks() {
    try {
        const response = await fetch(`${API_BASE}/books?limit=100`, {
            headers: { 'Authorization': `Bearer ${adminToken}` }
        });

        if (!response.ok) throw new Error('Failed to load books');

        const data = await response.json();
        allBooks = data.data || [];
        renderBooksTable(allBooks);
    } catch (error) {
        console.error('Error loading books:', error);
        document.getElementById('booksTable').innerHTML = `<div class="error-message">Failed to load books</div>`;
    }
}

function filterBooksTable() {
    const searchTerm = document.getElementById('searchBooks').value.toLowerCase();
    const filtered = allBooks.filter(book =>
        book.title.toLowerCase().includes(searchTerm) ||
        book.book_no.toLowerCase().includes(searchTerm) ||
        (book.author && book.author.toLowerCase().includes(searchTerm))
    );
    renderBooksTable(filtered);
}

function renderBooksTable(books) {
    const container = document.getElementById('booksTable');

    if (books.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">📚</div>
                <p>No books found.</p>
            </div>
        `;
        return;
    }

    const html = `
        <table>
            <thead>
                <tr>
                    <th>Cover</th>
                    <th>Book No</th>
                    <th>Title</th>
                    <th>Author</th>
                    <th>Category</th>
                    <th>Status</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                ${books.map(book => `
                    <tr>
                        <td><img src="${book.cover_image || '/static/images/default_book.svg'}" alt="${escapeHtml(book.title)}" class="book-thumbnail"></td>
                        <td>${escapeHtml(book.book_no)}</td>
                        <td>${escapeHtml(book.title)}</td>
                        <td>${escapeHtml(book.author || '-')}</td>
                        <td>${escapeHtml(book.category || '-')}</td>
                        <td><span class="status-badge status-${book.status.toLowerCase()}">${book.status}</span></td>
                        <td>
                            <div class="action-buttons">
                                <button class="btn-action" onclick="openEditModal('${escapeHtml(book.book_no)}')">Edit</button>
                                <button class="btn-action danger" onclick="deleteBook('${escapeHtml(book.book_no)}')">Delete</button>
                            </div>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;

    container.innerHTML = html;
}

function openEditModal(bookNo) {
    const book = allBooks.find(b => b.book_no === bookNo);
    if (!book) return;

    document.getElementById('editBookNo').value = book.book_no;
    document.getElementById('editBookTitle').value = book.title;
    document.getElementById('editBookAuthor').value = book.author || '';
    document.getElementById('editBookCategory').value = book.category || '';
    document.getElementById('editCoverImage').value = '';
    document.getElementById('editImagePreview').style.display = 'none';
    selectedEditImageFile = null;

    document.getElementById('editBookModal').style.display = 'flex';
}

function closeEditModal() {
    document.getElementById('editBookModal').style.display = 'none';
    document.getElementById('editBookError').style.display = 'none';
}

async function handleEditBook(event) {
    event.preventDefault();

    const bookNo = document.getElementById('editBookNo').value;
    const title = document.getElementById('editBookTitle').value.trim();
    const author = document.getElementById('editBookAuthor').value.trim();
    const category = document.getElementById('editBookCategory').value;
    const errorDiv = document.getElementById('editBookError');
    const submitBtn = event.target.querySelector('button[type="submit"]');

    errorDiv.style.display = 'none';

    if (!title) {
        errorDiv.textContent = 'Title is required';
        errorDiv.style.display = 'block';
        return;
    }

    try {
        const formData = new FormData();
        formData.append('book_no', bookNo);
        formData.append('title', title);
        if (author) formData.append('author', author);
        if (category) formData.append('category', category);
        if (selectedEditImageFile) formData.append('cover_image', selectedEditImageFile);

        submitBtn.disabled = true;
        submitBtn.textContent = 'Saving...';

        const response = await fetch(`${API_BASE}/admin/books/update`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${adminToken}`
            },
            body: formData
        });

        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || 'Failed to update book');
        }

        closeEditModal();
        loadBooks();
    } catch (error) {
        console.error('Error updating book:', error);
        errorDiv.textContent = error.message;
        errorDiv.style.display = 'block';
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = '💾 Save Changes';
    }
}

async function deleteBook(bookNo) {
    if (!confirm('Delete this book? This action cannot be undone.')) return;

    try {
        const response = await fetch(`${API_BASE}/admin/books/delete`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${adminToken}`
            },
            body: JSON.stringify({ book_no: bookNo })
        });

        const data = await response.json();

        if (data.blocked) {
            alert(`Cannot delete — this book has ${data.active_count} active reservation(s) or borrow(s). Resolve all transactions first.`);
            return;
        }

        if (!response.ok) {
            throw new Error(data.error || 'Failed to delete book');
        }

        loadBooks();
    } catch (error) {
        console.error('Error deleting book:', error);
        alert('Failed to delete book');
    }
}

async function loadUsers() {
    try {
        const schoolLevel = document.getElementById('filterSchoolLevel').value;
        const yearLevel = document.getElementById('filterYearLevel').value;
        const status = document.getElementById('filterStatus').value;

        const params = new URLSearchParams({ limit: 100 });
        if (schoolLevel) params.append('school_level', schoolLevel);
        if (yearLevel) params.append('year_level', yearLevel);
        if (status) params.append('status', status);

        const response = await fetch(`${API_BASE}/admin/users?${params}`, {
            headers: { 'Authorization': `Bearer ${adminToken}` }
        });

        if (!response.ok) throw new Error('Failed to load users');

        const data = await response.json();
        const users = data.data || [];

        const totalCount = users.length;
        const activeCount = users.filter(u => u.account_status_detail === 'active').length;
        const expiringCount = users.filter(u => u.account_status_detail === 'expiry_warned').length;

        document.getElementById('totalUsersCount').textContent = totalCount;
        document.getElementById('activeUsersCount').textContent = activeCount;
        document.getElementById('expiringUsersCount').textContent = expiringCount;

        renderUsersTable(users);
    } catch (error) {
        console.error('Error loading users:', error);
        document.getElementById('usersTable').innerHTML = `<div class="error-message">Failed to load users</div>`;
    }
}

function renderUsersTable(users) {
    const container = document.getElementById('usersTable');

    if (users.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">👥</div>
                <p>No users found.</p>
            </div>
        `;
        return;
    }

    const html = `
        <table>
            <thead>
                <tr>
                    <th>School ID</th>
                    <th>Name</th>
                    <th>Role</th>
                    <th>School Level</th>
                    <th>Year</th>
                    <th>Status</th>
                    <th>Expires At</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                ${users.map(user => `
                    <tr>
                        <td>${escapeHtml(user.school_id)}</td>
                        <td>${escapeHtml(user.name)}</td>
                        <td>${escapeHtml(user.role || '-')}</td>
                        <td>${escapeHtml(user.school_level || '-')}</td>
                        <td>${escapeHtml(user.year_level || '-')}</td>
                        <td><span class="status-badge" style="background: rgba(56, 189, 248, 0.1); color: var(--accent);">${user.account_status_detail || 'active'}</span></td>
                        <td>${formatDate(user.account_expires_at)}</td>
                        <td>
                            ${user.is_staff
                                ? '<button class="btn-action" disabled title="Admin accounts are not renewed here">Renew</button>'
                                : `<button class="btn-action" onclick="openRenewModal('${escapeHtml(user.school_id)}')">Renew</button>`
                            }
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;

    container.innerHTML = html;
}

function openRenewModal(schoolId) {
    document.getElementById('renewUserId').value = schoolId;
    document.getElementById('renewYears').value = '1';
    document.getElementById('renewError').style.display = 'none';
    document.getElementById('renewUserModal').style.display = 'flex';
}

function closeRenewModal() {
    document.getElementById('renewUserModal').style.display = 'none';
}

async function handleRenewUser(event) {
    event.preventDefault();

    const schoolId = document.getElementById('renewUserId').value;
    const extendYears = parseInt(document.getElementById('renewYears').value, 10);
    const errorDiv = document.getElementById('renewError');
    const submitBtn = event.target.querySelector('button[type="submit"]');

    errorDiv.style.display = 'none';

    if (extendYears < 1) {
        errorDiv.textContent = 'Years must be at least 1';
        errorDiv.style.display = 'block';
        return;
    }

    try {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Renewing...';

        const response = await fetch(`${API_BASE}/admin/users/renew`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${adminToken}`
            },
            body: JSON.stringify({ school_id: schoolId, extend_years: extendYears })
        });

        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || 'Failed to renew account');
        }

        closeRenewModal();
        loadUsers();
    } catch (error) {
        console.error('Error renewing account:', error);
        errorDiv.textContent = error.message;
        errorDiv.style.display = 'block';
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = '✓ Renew Account';
    }
}

async function loadCourses() {
    try {
        const response = await fetch(`${API_BASE}/courses`);
        if (!response.ok) throw new Error('Failed to load courses');
        const data = await response.json();
        availableCourses = data.courses || [];
        populateCourseOptions();
    } catch (error) {
        console.error('Error loading courses:', error);
    }
}

function populateCourseOptions() {
    const select = document.getElementById('newUserCourse');
    if (!select) return;
    select.innerHTML = '<option value="">Select course</option>' +
        availableCourses.map(course => `<option value="${escapeHtml(course)}">${escapeHtml(course)}</option>`).join('');
}

function handleRoleChange() {
    const role = document.getElementById('newUserRole').value;
    const studentFields = document.getElementById('studentFields');
    const schoolLevel = document.getElementById('newUserSchoolLevel');
    const yearLevel = document.getElementById('newUserYearLevel');
    const course = document.getElementById('newUserCourse');

    if (role === 'Student') {
        studentFields.style.display = 'block';
        schoolLevel.required = true;
        yearLevel.required = true;
        handleSchoolLevelChange();
    } else {
        studentFields.style.display = 'none';
        schoolLevel.required = false;
        yearLevel.required = false;
        course.required = false;
    }
}

function handleSchoolLevelChange() {
    const schoolLevel = document.getElementById('newUserSchoolLevel').value;
    const yearSelect = document.getElementById('newUserYearLevel');
    const courseField = document.getElementById('courseField');
    const courseSelect = document.getElementById('newUserCourse');

    const options = schoolLevel === 'College'
        ? ['1st Year', '2nd Year', '3rd Year', '4th Year']
        : ['Grade 7', 'Grade 8', 'Grade 9', 'Grade 10'];

    yearSelect.innerHTML = options.map(opt => `<option value="${opt}">${opt}</option>`).join('');

    if (schoolLevel === 'College') {
        courseField.style.display = 'block';
        courseSelect.required = true;
    } else {
        courseField.style.display = 'none';
        courseSelect.required = false;
        courseSelect.value = '';
    }
}

async function handleAddUser(event) {
    event.preventDefault();
    const errorDiv = document.getElementById('addUserError');
    const successDiv = document.getElementById('addUserSuccess');
    const submitBtn = event.target.querySelector('button[type="submit"]');

    errorDiv.style.display = 'none';
    successDiv.style.display = 'none';

    const role = document.getElementById('newUserRole').value;
    const schoolLevel = document.getElementById('newUserSchoolLevel').value;
    const payload = {
        role: role.toLowerCase(),
        school_id: document.getElementById('newUserSchoolId').value.trim(),
        name: document.getElementById('newUserName').value.trim(),
        password: document.getElementById('newUserPassword').value
    };

    if (role === 'Student') {
        payload.school_level = schoolLevel;
        payload.year_level = document.getElementById('newUserYearLevel').value;
        if (schoolLevel === 'College') {
            payload.course = document.getElementById('newUserCourse').value;
        }
    }

    try {
        submitBtn.disabled = true;
        submitBtn.textContent = 'Adding...';
        const response = await fetch(`${API_BASE}/admin/users/create`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${adminToken}`
            },
            body: JSON.stringify(payload)
        });
        const data = await response.json();
        if (!response.ok) {
            throw new Error(data.error || 'Failed to create user');
        }

        successDiv.textContent = data.message || 'User created successfully';
        successDiv.style.display = 'block';
        showToast('✅ User added successfully');
        resetAddUserForm();
        loadUsers();
        setTimeout(() => { successDiv.style.display = 'none'; }, 2400);
    } catch (error) {
        errorDiv.textContent = error.message;
        errorDiv.style.display = 'block';
    } finally {
        submitBtn.disabled = false;
        submitBtn.textContent = '➕ Add User';
    }
}

function resetAddUserForm() {
    const form = document.getElementById('addUserForm');
    form.reset();
    document.getElementById('newUserRole').value = 'Student';
    document.getElementById('addUserError').style.display = 'none';
    document.getElementById('addUserSuccess').style.display = 'none';
    handleSchoolLevelChange();
    handleRoleChange();
}

function showToast(message) {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    const toast = document.createElement('div');
    toast.className = 'toast';
    toast.textContent = message;
    container.appendChild(toast);
    setTimeout(() => toast.classList.add('show'), 10);
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 200);
    }, 2200);
}

async function loadReports() {
    try {
        const booksResponse = await fetch(`${API_BASE}/books?limit=1`, {
            headers: { 'Authorization': `Bearer ${adminToken}` }
        });
        const bookData = await booksResponse.json();

        const usersResponse = await fetch(`${API_BASE}/admin/users?limit=1`, {
            headers: { 'Authorization': `Bearer ${adminToken}` }
        });
        const userData = await usersResponse.json();

        document.getElementById('totalBooksReport').textContent = bookData.pagination?.total || '0';
        document.getElementById('totalUsersReport').textContent = userData.pagination?.total || '0';
        document.getElementById('activeReservationsReport').textContent = '0';
        document.getElementById('borrowedBooksReport').textContent = '0';

        const allBooks = await fetch(`${API_BASE}/books?limit=1000`, {
            headers: { 'Authorization': `Bearer ${adminToken}` }
        }).then(r => r.json());

        const statusCounts = {
            'Available': 0,
            'Pending': 0,
            'Reserved': 0,
            'Borrowed': 0
        };

        (allBooks.data || []).forEach(book => {
            if (statusCounts.hasOwnProperty(book.status)) {
                statusCounts[book.status]++;
            }
        });

        const total = Object.values(statusCounts).reduce((a, b) => a + b, 0) || 1;

        const html = Object.entries(statusCounts).map(([status, count]) => {
            const percentage = ((count / total) * 100).toFixed(1);
            return `
                <tr>
                    <td>${status}</td>
                    <td>${count}</td>
                    <td>${percentage}%</td>
                </tr>
            `;
        }).join('');

        document.getElementById('statusDistribution').innerHTML = html;
    } catch (error) {
        console.error('Error loading reports:', error);
    }
}

function formatDate(dateString) {
    if (!dateString) return '-';
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric'
    });
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function logoutAdmin() {
    localStorage.removeItem('adminToken');
    localStorage.removeItem('adminProfile');
    window.location.href = '/';
}

window.addEventListener('click', (e) => {
    const editModal = document.getElementById('editBookModal');
    const renewModal = document.getElementById('renewUserModal');

    if (e.target === editModal) closeEditModal();
    if (e.target === renewModal) closeRenewModal();
});
