const API_BASE = '/api';
const CURRENT_DATE = new Date();

let studentToken = localStorage.getItem('studentToken');
let studentProfile = null;

document.addEventListener('DOMContentLoaded', async () => {
    await verifyAccess();
    updateDate();
    loadStudentProfile();
    initializeEventListeners();
    loadReservations();
});

async function verifyAccess() {
    if (!studentToken) {
        window.location.href = '/';
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/my/profile`, {
            headers: { 'Authorization': `Bearer ${studentToken}` }
        });

        if (!response.ok) {
            localStorage.removeItem('studentToken');
            localStorage.removeItem('studentProfile');
            localStorage.removeItem('accountStatus');
            window.location.href = '/';
            return;
        }

        const data = await response.json();
        studentProfile = data;
        localStorage.setItem('studentProfile', JSON.stringify(data));
        localStorage.setItem('accountStatus', data.account_status_detail || 'active');

        if (data.account_status_detail === 'expired') {
            showExpiryBanner();
            disableExpiredFeatures();
        }
    } catch (error) {
        console.error('Verification error:', error);
        window.location.href = '/';
    }
}

function showExpiryBanner() {
    document.getElementById('expiryBanner').style.display = 'flex';
}

function disableExpiredFeatures() {
    document.getElementById('reservationsNav').disabled = true;
    document.getElementById('reservationsNav').style.opacity = '0.5';
    document.getElementById('borrowsNav').disabled = true;
    document.getElementById('borrowsNav').style.opacity = '0.5';
    document.getElementById('chatNav').disabled = true;
    document.getElementById('chatNav').style.opacity = '0.5';
}

function closeBanner() {
    document.getElementById('expiryBanner').style.display = 'none';
}

function updateDate() {
    const options = { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' };
    const dateStr = CURRENT_DATE.toLocaleDateString('en-US', options);
    document.getElementById('currentDate').textContent = dateStr;
}

function loadStudentProfile() {
    if (!studentProfile) {
        studentProfile = JSON.parse(localStorage.getItem('studentProfile')) || {};
    }

    const greeting = getGreeting();
    document.getElementById('greeting').textContent = greeting;
    document.getElementById('studentName').textContent = studentProfile.name || 'Student';
    document.getElementById('studentId').textContent = studentProfile.school_id || '-';
    document.getElementById('studentAvatar').src = studentProfile.photo || '/static/images/avatar_fox.svg';

    document.getElementById('infoName').textContent = studentProfile.name || '-';
    document.getElementById('infoSchoolId').textContent = studentProfile.school_id || '-';
    document.getElementById('infoSchoolLevel').textContent = studentProfile.school_level || '-';
    document.getElementById('infoYearLevel').textContent = studentProfile.year_level || '-';

    if (studentProfile.course) {
        document.getElementById('infoCourseRow').style.display = 'flex';
        document.getElementById('infoCourse').textContent = studentProfile.course;
    }

    document.getElementById('phoneNumber').value = studentProfile.phone_number || '';
    document.getElementById('email').value = studentProfile.email || '';
    document.getElementById('photoPreview').src = studentProfile.photo || '/static/images/avatar_fox.svg';

    if (studentProfile.account_expires_at) {
        const expiryDate = new Date(studentProfile.account_expires_at);
        const expiryText = expiryDate.toLocaleDateString('en-US', {
            year: 'numeric',
            month: 'long',
            day: 'numeric'
        });
        let expiryHtml = `<strong>Account expires: ${expiryText}</strong>`;

        if (studentProfile.account_status_detail === 'expiry_warned') {
            expiryHtml += '<p style="margin: 8px 0 0 0; color: var(--warning);">Your account expires soon. Contact the librarian to renew.</p>';
        }

        document.getElementById('expiryCard').innerHTML = expiryHtml;
    }
}

function getGreeting() {
    const hour = new Date().getHours();
    if (hour < 12) return `Good morning, ${studentProfile.name || 'Student'}!`;
    if (hour < 18) return `Good afternoon, ${studentProfile.name || 'Student'}!`;
    return `Good evening, ${studentProfile.name || 'Student'}!`;
}

function initializeEventListeners() {
    document.addEventListener('keypress', (e) => {
        if (e.key === 'Enter' && document.activeElement.id === 'messageInput') {
            sendMessage(e);
        }
    });
}

function switchPanel(panelName) {
    const panels = document.querySelectorAll('.content-panel');
    panels.forEach(p => p.classList.remove('active'));

    const navItems = document.querySelectorAll('.nav-item');
    navItems.forEach(n => n.classList.remove('active'));

    let panelId, navItem;
    switch (panelName) {
        case 'reservations':
            panelId = 'reservationsPanel';
            navItem = document.getElementById('reservationsNav');
            break;
        case 'notifications':
            panelId = 'notificationsPanel';
            navItem = document.querySelector('.nav-item:nth-child(2)');
            loadNotifications();
            break;
        case 'borrows':
            panelId = 'borrowsPanel';
            navItem = document.getElementById('borrowsNav');
            loadBorrows();
            break;
        case 'history':
            panelId = 'historyPanel';
            navItem = document.getElementById('historyNav');
            loadHistory();
            break;
        case 'chat':
            panelId = 'chatPanel';
            navItem = document.getElementById('chatNav');
            break;
        case 'settings':
            panelId = 'settingsPanel';
            navItem = document.getElementById('settingsNav');
            break;
    }

    if (panelId) {
        document.getElementById(panelId).classList.add('active');
    }
    if (navItem) {
        navItem.classList.add('active');
    }
}

async function loadReservations() {
    try {
        const response = await fetch(`${API_BASE}/my/transactions`, {
            headers: { 'Authorization': `Bearer ${studentToken}` }
        });

        if (!response.ok) throw new Error('Failed to load reservations');

        const data = await response.json();
        const transactions = data.data || [];

        const pending = transactions.filter(t => t.status === 'Pending').length;
        const reserved = transactions.filter(t => t.status === 'Reserved').length;
        const borrowed = transactions.filter(t => t.status === 'Borrowed').length;
        const returned = transactions.filter(t => t.status === 'Returned').length;

        document.getElementById('activeReservations').textContent = pending + reserved;
        document.getElementById('currentlyBorrowed').textContent = borrowed;
        document.getElementById('booksReturned').textContent = returned;

        renderReservationsTable(transactions.filter(t => ['Pending', 'Reserved', 'Borrowed'].includes(t.status)));
    } catch (error) {
        console.error('Error loading reservations:', error);
        document.getElementById('reservationsTable').innerHTML = `<div class="error-message">Failed to load reservations</div>`;
    }
}

function renderReservationsTable(reservations) {
    const container = document.getElementById('reservationsTable');

    if (reservations.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">📚</div>
                <p>No active reservations yet.</p>
            </div>
        `;
        return;
    }

    const html = `
        <table>
            <thead>
                <tr>
                    <th>Title</th>
                    <th>Status</th>
                    <th>Date Reserved</th>
                    <th>Queue Position</th>
                    <th>Deadline</th>
                    <th>Actions</th>
                </tr>
            </thead>
            <tbody>
                ${reservations.map(t => `
                    <tr>
                        <td>${escapeHtml(t.book_title)}</td>
                        <td><span class="status-badge status-${t.status.toLowerCase()}">${t.status}</span></td>
                        <td>${formatDate(t.date_reserved)}</td>
                        <td>${t.queue_position || '-'}</td>
                        <td>${t.pickup_deadline || t.return_due_date || '-'}</td>
                        <td>
                            <div class="action-buttons">
                                ${t.status === 'Pending' || t.status === 'Reserved' ? `<button class="btn-action" onclick="cancelReservation('${t.transaction_id}')">Cancel</button>` : ''}
                                ${t.status === 'Borrowed' ? `<button class="btn-action" onclick="viewBorrowDetails('${t.transaction_id}')">Details</button>` : ''}
                            </div>
                        </td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;

    container.innerHTML = html;
}

async function cancelReservation(transactionId) {
    if (!confirm('Cancel this reservation?')) return;

    try {
        const response = await fetch(`${API_BASE}/admin/reservations/cancel`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${studentToken}`
            },
            body: JSON.stringify({ transaction_id: transactionId })
        });

        if (!response.ok) throw new Error('Failed to cancel');

        loadReservations();
    } catch (error) {
        console.error('Error cancelling reservation:', error);
        alert('Failed to cancel reservation');
    }
}

function viewBorrowDetails(transactionId) {
    alert(`Viewing details for transaction: ${transactionId}`);
}

async function loadNotifications() {
    try {
        const response = await fetch(`${API_BASE}/my/notifications`, {
            headers: { 'Authorization': `Bearer ${studentToken}` }
        });

        if (!response.ok) throw new Error('Failed to load notifications');

        const data = await response.json();
        const notifications = data.data || [];

        const unreadCount = notifications.filter(n => !n.is_read).length;
        if (unreadCount > 0) {
            document.getElementById('notificationBadge').textContent = unreadCount;
            document.getElementById('notificationBadge').style.display = 'flex';
        } else {
            document.getElementById('notificationBadge').style.display = 'none';
        }

        renderNotificationsList(notifications);
    } catch (error) {
        console.error('Error loading notifications:', error);
        document.getElementById('notificationsList').innerHTML = `<div class="error-message">Failed to load notifications</div>`;
    }
}

function renderNotificationsList(notifications) {
    const container = document.getElementById('notificationsList');

    if (notifications.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">🔔</div>
                <p>No notifications.</p>
            </div>
        `;
        return;
    }

    container.innerHTML = notifications.map(n => `
        <div class="notification-item ${n.is_read ? '' : 'unread'}" onclick="markNotificationRead('${n.notification_id}')">
            <div class="notification-header">
                <span class="notification-title">${escapeHtml(n.title)}</span>
                <span class="notification-timestamp">${getRelativeTime(n.created_at)}</span>
            </div>
            <div class="notification-message">${escapeHtml(n.message)}</div>
        </div>
    `).join('');
}

async function markNotificationRead(notificationId) {
    try {
        await fetch(`${API_BASE}/my/notifications/read`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${studentToken}`
            },
            body: JSON.stringify({ notification_id: notificationId })
        });
        loadNotifications();
    } catch (error) {
        console.error('Error marking notification read:', error);
    }
}

async function markAllNotificationsRead() {
    try {
        await fetch(`${API_BASE}/my/notifications/read`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${studentToken}`
            },
            body: JSON.stringify({ mark_all: true })
        });
        loadNotifications();
    } catch (error) {
        console.error('Error marking all as read:', error);
    }
}

async function loadBorrows() {
    try {
        const response = await fetch(`${API_BASE}/my/transactions`, {
            headers: { 'Authorization': `Bearer ${studentToken}` }
        });

        if (!response.ok) throw new Error('Failed to load borrows');

        const data = await response.json();
        const borrows = (data.data || []).filter(t => t.status === 'Borrowed' || t.status === 'Unreturned');

        renderBorrowsList(borrows);
    } catch (error) {
        console.error('Error loading borrows:', error);
        document.getElementById('borrowsList').innerHTML = `<div class="error-message">Failed to load borrows</div>`;
    }
}

function renderBorrowsList(borrows) {
    const container = document.getElementById('borrowsList');

    if (borrows.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">📖</div>
                <p>You haven't borrowed any books yet.</p>
            </div>
        `;
        return;
    }

    container.innerHTML = borrows.map(borrow => {
        const dueDate = new Date(borrow.return_due_date);
        const today = new Date();
        const daysLeft = Math.ceil((dueDate - today) / (1000 * 60 * 60 * 24));

        let dueDateClass = 'duedate-green';
        if (daysLeft < 3) dueDateClass = 'duedate-red';
        else if (daysLeft < 7) dueDateClass = 'duedate-amber';

        const overdueBanner = borrow.status === 'Unreturned' ? '<div class="overdue-banner">⚠️ OVERDUE — Please return immediately</div>' : '';

        return `
            <div class="borrow-card">
                <img src="${borrow.cover_image || '/static/images/default_book.svg'}" alt="${escapeHtml(borrow.book_title)}" class="borrow-cover">
                <div class="borrow-content">
                    ${overdueBanner}
                    <div class="borrow-title">${escapeHtml(borrow.book_title)}</div>
                    <div class="borrow-author">${escapeHtml(borrow.student_name || 'Unknown')}</div>
                    <div class="borrow-info">
                        <div>Borrowed: ${formatDate(borrow.date_borrowed)}</div>
                        <div>Approved by: ${escapeHtml(borrow.approved_by_name || '-')}</div>
                    </div>
                    <div class="borrow-duedate ${dueDateClass}">Due: ${formatDate(borrow.return_due_date)}</div>
                </div>
            </div>
        `;
    }).join('');
}

async function loadHistory() {
    try {
        const response = await fetch(`${API_BASE}/my/transactions`, {
            headers: { 'Authorization': `Bearer ${studentToken}` }
        });

        if (!response.ok) throw new Error('Failed to load history');

        const data = await response.json();
        const history = (data.data || []).filter(t => ['Returned', 'Cancelled', 'Expired', 'Unreturned'].includes(t.status));

        renderHistoryTable(history);
    } catch (error) {
        console.error('Error loading history:', error);
        document.getElementById('historyTable').innerHTML = `<div class="error-message">Failed to load history</div>`;
    }
}

function renderHistoryTable(history) {
    const container = document.getElementById('historyTable');

    if (history.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-icon">🕒</div>
                <p>No transaction history.</p>
            </div>
        `;
        return;
    }

    const html = `
        <table>
            <thead>
                <tr>
                    <th>Title</th>
                    <th>Status</th>
                    <th>Date Reserved</th>
                    <th>Date Returned</th>
                </tr>
            </thead>
            <tbody>
                ${history.map(t => `
                    <tr>
                        <td>${escapeHtml(t.book_title)}</td>
                        <td><span class="status-badge status-${t.status.toLowerCase()}">${t.status}</span></td>
                        <td>${formatDate(t.date_reserved)}</td>
                        <td>${formatDate(t.date_returned) || formatDate(t.updated_at) || '-'}</td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;

    container.innerHTML = html;
}

function sendMessage(event) {
    event.preventDefault();
    const messageInput = document.getElementById('messageInput');
    const message = messageInput.value.trim();

    if (!message) return;

    const chatThread = document.getElementById('chatThread');
    if (chatThread.querySelector('.empty-state')) {
        chatThread.innerHTML = '';
    }

    const messageTime = new Date().toLocaleTimeString('en-US', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: true
    });

    const messageHtml = `
        <div class="chat-message student">
            <div class="chat-bubble">${escapeHtml(message)}</div>
        </div>
    `;

    chatThread.innerHTML += messageHtml;
    messageInput.value = '';
    chatThread.scrollTop = chatThread.scrollHeight;

    setTimeout(() => {
        const response = 'Thanks for your message! A librarian will respond soon.';
        const responseHtml = `
            <div class="chat-message librarian">
                <div class="chat-bubble">${response}</div>
            </div>
        `;
        chatThread.innerHTML += responseHtml;
        chatThread.scrollTop = chatThread.scrollHeight;
    }, 1000);
}

function showAvatarPicker() {
    document.getElementById('avatarPicker').style.display = document.getElementById('avatarPicker').style.display === 'none' ? 'block' : 'none';
}

function selectAvatar(filename) {
    document.getElementById('photoPreview').src = `/static/images/${filename}`;
    const avatars = document.querySelectorAll('.avatar-option');
    avatars.forEach(a => {
        a.classList.remove('selected');
        if (a.src.includes(filename)) {
            a.classList.add('selected');
        }
    });
}

function handlePhotoUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
        document.getElementById('photoPreview').src = e.target.result;
    };
    reader.readAsDataURL(file);
}

async function saveSettings() {
    const phoneNumber = document.getElementById('phoneNumber').value.trim();
    const email = document.getElementById('email').value.trim();

    if (!phoneNumber || !email) {
        showError('settingsError', 'Please fill in all required fields');
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/my/profile`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${studentToken}`
            },
            body: JSON.stringify({
                phone_number: phoneNumber,
                email: email
            })
        });

        if (!response.ok) throw new Error('Failed to save');

        showSuccess('settingsSuccess', 'Settings saved successfully!');
        loadStudentProfile();
    } catch (error) {
        console.error('Error saving settings:', error);
        showError('settingsError', 'Failed to save settings');
    }
}

function changePassword() {
    document.getElementById('changePasswordModal').style.display = 'flex';
}

function closePasswordModal() {
    document.getElementById('changePasswordModal').style.display = 'none';
    document.getElementById('passwordError').style.display = 'none';
}

async function submitPasswordChange(event) {
    event.preventDefault();

    const currentPassword = document.getElementById('currentPassword').value;
    const newPassword = document.getElementById('newPassword').value;
    const confirmPassword = document.getElementById('confirmPassword').value;
    const errorDiv = document.getElementById('passwordError');

    errorDiv.style.display = 'none';

    if (newPassword !== confirmPassword) {
        errorDiv.textContent = 'New passwords do not match';
        errorDiv.style.display = 'block';
        return;
    }

    if (newPassword.length < 8) {
        errorDiv.textContent = 'Password must be at least 8 characters';
        errorDiv.style.display = 'block';
        return;
    }

    try {
        const response = await fetch(`${API_BASE}/my/profile/update-password`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${studentToken}`
            },
            body: JSON.stringify({
                current_password: currentPassword,
                new_password: newPassword
            })
        });

        if (!response.ok) {
            const data = await response.json();
            throw new Error(data.error || 'Failed to change password');
        }

        alert('Password changed successfully!');
        closePasswordModal();
        document.querySelector('form').reset();
    } catch (error) {
        console.error('Error changing password:', error);
        errorDiv.textContent = error.message;
        errorDiv.style.display = 'block';
    }
}

function logout() {
    localStorage.removeItem('studentToken');
    localStorage.removeItem('studentProfile');
    localStorage.removeItem('accountStatus');
    window.location.href = '/';
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

function getRelativeTime(dateString) {
    const date = new Date(dateString);
    const now = new Date();
    const diff = now - date;

    const minutes = Math.floor(diff / 60000);
    const hours = Math.floor(diff / 3600000);
    const days = Math.floor(diff / 86400000);

    if (minutes < 1) return 'Just now';
    if (minutes < 60) return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
    if (hours < 24) return `${hours} hour${hours > 1 ? 's' : ''} ago`;
    if (days === 1) return 'Yesterday';
    if (days < 7) return `${days} days ago`;

    return date.toLocaleDateString('en-US', {
        month: 'short',
        day: 'numeric'
    });
}

function showError(elementId, message) {
    const element = document.getElementById(elementId);
    element.textContent = message;
    element.style.display = 'block';
    setTimeout(() => {
        element.style.display = 'none';
    }, 5000);
}

function showSuccess(elementId, message) {
    const element = document.getElementById(elementId);
    element.textContent = message;
    element.style.display = 'block';
    setTimeout(() => {
        element.style.display = 'none';
    }, 4000);
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

window.addEventListener('click', (e) => {
    const modal = document.getElementById('changePasswordModal');
    if (e.target === modal) {
        closePasswordModal();
    }
});
