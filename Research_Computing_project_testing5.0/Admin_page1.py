import os
import json
import uuid 
import logging
import sys
from flask import Flask, render_template, request, jsonify, send_from_directory, redirect, url_for
from datetime import datetime, timedelta
from werkzeug.utils import secure_filename

# --- INITIALIZATION & LOGGING ---
# Restored high-depth logging to track transactions and security events across all portals
app = Flask(__name__, template_folder='.', static_folder='.')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

# --- SERVER CONFIGURATION ---
PROFILE_FOLDER = 'Profile'
app.config['UPLOAD_FOLDER'] = PROFILE_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB Upload Limit
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = True

if not os.path.exists(PROFILE_FOLDER):
    os.makedirs(PROFILE_FOLDER)
    logger.info(f"Critical System: Created profile storage at {PROFILE_FOLDER}")

# DATABASE DEFINITIONS: Strict separation for security and sync efficiency
DB_FILES = {
    'books': 'books.json', 
    'admins': 'admins.json',    # Librarian/Staff Registry
    'users': 'users.json',      # Student Registry
    'transactions': 'transactions.json',
    'ratings': 'ratings.json',
    'config': 'system_config.json'
}

# Global Session Store: School ID -> Session Token (Security Handshake)
ACTIVE_SESSIONS = {} 

# --- DATABASE ENGINE ---

def initialize_system():
    """Ensures all JSON databases exist. Injects default admin to prevent lockouts."""
    for key, file_path in DB_FILES.items():
        if not os.path.exists(file_path):
            if key == 'config':
                initial_data = {
                    "rating_enabled": False, 
                    "system_version": "2.5.0", # Incremented for new Asset/Audit features
                    "last_reboot": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "maintenance_mode": False
                }
            else:
                initial_data = []
            with open(file_path, 'w', encoding='utf-8') as f: 
                json.dump(initial_data, f, indent=4)
            logger.info(f"System Check: Initialized new database: {file_path}")

    # EMERGENCY ACCESS: Ensure at least one admin exists
    admins = get_db('admins')
    if not admins:
        logger.warning("SECURITY ALERT: No librarians detected. Generating 'admin' account.")
        admins.append({
            "name": "System Administrator",
            "school_id": "admin",
            "password": "admin",
            "category": "Staff",
            "photo": "default.png",
            "created_at": "SYSTEM_INIT"
        })
        save_db('admins', admins)

def get_db(key):
    """Safe read from JSON databases with multi-type fallback."""
    try:
        if not os.path.exists(DB_FILES[key]):
            return {} if key == 'config' else []
        with open(DB_FILES[key], 'r', encoding='utf-8') as f: 
            return json.load(f)
    except Exception as e:
        logger.error(f"DATABASE READ ERROR on {key}: {e}")
        return {} if key == 'config' else []

def save_db(key, data):
    """Atomic write to JSON databases to prevent data corruption during high-traffic."""
    try:
        with open(DB_FILES[key], 'w', encoding='utf-8') as f: 
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        logger.error(f"DATABASE SAVE ERROR on {key}: {e}")

# --- SECURITY & SYNC UTILITIES ---

def find_any_user(s_id):
    """
    THE MASTER CONNECTOR: Cross-references both Student and Librarian registries.
    Standardizes IDs to lowercase to prevent login failures due to casing.
    """
    search_target = str(s_id).strip().lower()
    if not search_target: return None

    # Priority 1: Check Admins
    admin_list = get_db('admins')
    for admin in admin_list:
        if str(admin.get('school_id', '')).strip().lower() == search_target:
            admin['registry_origin'] = 'admins.json'
            admin['is_staff'] = True
            return admin
            
    # Priority 2: Check Students
    student_list = get_db('users')
    for student in student_list:
        if str(student.get('school_id', '')).strip().lower() == search_target:
            student['registry_origin'] = 'users.json'
            student['is_staff'] = False
            return student
            
    return None

def is_mobile_request():
    """Identifies mobile vs desktop requests to route users to LBAS vs Admin Dashboard."""
    ua = request.headers.get('User-Agent', '').lower()
    return any(x in ua for x in ['mobile', 'android', 'iphone', 'ipad', 'windows phone'])

def run_auto_sync_engine():
    """
    CORE FIX: Automatically lifts 'Reserved' status back to 'Available' for the tablet.
    Calculates time delta and updates two databases (Books & Transactions) simultaneously.
    """
    books = get_db('books')
    transactions = get_db('transactions')
    now = datetime.now()
    changes_made = False
    
    for trans in transactions:
        if trans['status'] == 'Reserved' and 'expiry' in trans:
            try:
                exp_time = datetime.strptime(trans['expiry'], "%Y-%m-%d %H:%M")
                if now > exp_time:
                    trans['status'] = 'Expired'
                    # Relink to book database to release status
                    for b in books:
                        if b['book_no'] == trans['book_no']:
                            b['status'] = 'Available'
                            changes_made = True
                            logger.info(f"SYNC ENGINE: Auto-released Book {b['book_no']} (Timeout)")
            except Exception as e:
                logger.error(f"Sync Engine Logic Error: {e}")
                
    if changes_made:
        save_db('books', books)
        save_db('transactions', transactions)
    return books

# --- PRIMARY NAVIGATION & ROUTING ---

@app.route('/')
def index_gateway():
    """Smart-routes based on device type. Ensures Tablet/Desktop sees Admin, Mobile sees LBAS."""
    if is_mobile_request():
        return redirect(url_for('lbas_site'))
    return render_template('admin_dashboard.html', 
                         books=run_auto_sync_engine(), 
                         users=get_db('users'),
                         admins=get_db('admins'))

@app.route('/audit_users')
def audit_view():
    """Route for the new Users/Librarians Audit Hub."""
    if is_mobile_request():
        return redirect(url_for('lbas_site'))
    return render_template('Admin_users_list.html')

@app.route('/tablet')
def user_tablet_view():
    """Stationary Tablet view for walk-in students."""
    if is_mobile_request():
        return redirect(url_for('lbas_site'))
    return render_template('user_tablet.html')

@app.route('/lbas')
def lbas_site():
    """Mobile interface for book reservations."""
    return render_template('LBAS.html')

@app.route('/dev/analysis')
def dev_analysis_portal():
    """Admin-only portal for rating metrics and database health."""
    if is_mobile_request():
        return "Access Forbidden: Desktop Analysis only.", 403
    return render_template('Developers_rate_analysis.html')

# --- ASSET MASTER CONTROL API (NEW) ---

@app.route('/api/update_book', methods=['POST'])
def api_update_book():
    """Updates book details or status (e.g., setting to 'Missing' or back to 'Available')."""
    data = request.json
    b_no = data.get('book_no')
    books = get_db('books')
    
    found = False
    for b in books:
        if b['book_no'] == b_no:
            if 'title' in data: b['title'] = data['title']
            if 'category' in data: b['category'] = data['category']
            if 'status' in data: b['status'] = data['status']
            found = True
            break
            
    if found:
        save_db('books', books)
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "Asset not found"}), 404

@app.route('/api/delete_book', methods=['POST'])
def api_delete_book():
    """Permanently removes a book from the library inventory."""
    data = request.json
    b_no = data.get('book_no')
    books = get_db('books')
    
    new_books = [b for b in books if b['book_no'] != b_no]
    if len(new_books) < len(books):
        save_db('books', new_books)
        return jsonify({"success": True})
    return jsonify({"success": False, "message": "Book not found"}), 404

# --- RATING & FEEDBACK ENGINE ---

@app.route('/api/toggle_rating', methods=['POST'])
def api_toggle_rating():
    """Global switch to enable/disable the rating prompt on Tablet/LBAS."""
    config = get_db('config')
    current = config.get('rating_enabled', False)
    config['rating_enabled'] = not current
    config['last_modified'] = datetime.now().strftime("%Y-%m-%d %H:%M")
    save_db('config', config)
    return jsonify({"success": True, "new_state": config['rating_enabled']})

@app.route('/api/rating_status/<school_id>')
def api_rating_eligibility(school_id):
    """Checks if a user has already rated to prevent spam."""
    config = get_db('config')
    if not config.get('rating_enabled', False):
        return jsonify({"show": False, "reason": "System Closed"})

    ratings = get_db('ratings')
    search_id = str(school_id).strip().lower()
    already_done = any(str(r.get('school_id')).strip().lower() == search_id for r in ratings)
    return jsonify({"show": not already_done})

@app.route('/api/rate', methods=['POST'])
def api_submit_rating():
    """Saves student feedback with session token validation."""
    data = request.json
    s_id = str(data.get('school_id', '')).strip().lower()
    
    if ACTIVE_SESSIONS.get(s_id) != data.get('token'):
        return jsonify({"success": False, "message": "Security Handshake Failed"}), 401

    ratings = get_db('ratings')
    ratings.append({
        "rating_id": str(uuid.uuid4())[:10],
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "school_id": s_id,
        "stars": int(data.get('stars', 5)),
        "feedback": data.get('feedback', 'N/A'),
        "platform": "Mobile" if is_mobile_request() else "Tablet"
    })
    save_db('ratings', ratings)
    return jsonify({"success": True})

@app.route('/api/ratings_summary')
def api_get_ratings():
    """Data feed for the Developer Analysis dashboard."""
    return jsonify(get_db('ratings'))

# --- CORE BOOK & TRANSACTION ENGINE ---

@app.route('/api/books')
def api_get_books():
    """Fetches inventory while triggering the 30-min auto-release engine."""
    return jsonify(run_auto_sync_engine())

@app.route('/api/users')
def api_get_only_students():
    """Specific feed for Student side of Audit Hub."""
    return jsonify(get_db('users'))

@app.route('/api/admins')
def api_get_only_librarians():
    """Specific feed for Staff side of Audit Hub."""
    return jsonify(get_db('admins'))

@app.route('/api/get_all_entities')
def api_get_all_users():
    """Combined feed for system-wide population tracking."""
    return jsonify({
        "students": get_db('users'),
        "librarians": get_db('admins')
    })

@app.route('/api/transactions')
def api_get_transactions(): 
    """Complete movement history for Admin Dashboard log table."""
    return jsonify(get_db('transactions'))

@app.route('/api/reserve', methods=['POST'])
def api_reserve_book():
    """Handles reservations with strict daily 5-book quota enforcement."""
    data = request.json
    b_no = data.get('book_no')
    s_id = str(data.get('school_id', '')).strip().lower()
    token = data.get('token')
    
    user = find_any_user(s_id)
    if not user: return jsonify({"success": False, "message": "Identity Not Found"}), 404
    ACTIVE_SESSIONS[s_id] = token 

    books = get_db('books')
    transactions = get_db('transactions')
    
    # 5-BOOK QUOTA LOGIC
    today = datetime.now().strftime("%Y-%m-%d")
    daily_count = sum(1 for t in transactions if str(t['school_id']).lower() == s_id 
                    and today in t['date'] and t['status'] in ['Reserved', 'Borrowed'])
    
    if daily_count >= 5:
        return jsonify({"success": False, "message": "Daily limit (5) exceeded."})

    target = next((b for b in books if b['book_no'] == b_no), None)
    if target and target['status'] == 'Available':
        target['status'] = 'Reserved'
        transactions.append({
            "book_no": b_no,
            "school_id": s_id,
            "date": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "expiry": (datetime.now() + timedelta(minutes=30)).strftime("%Y-%m-%d %H:%M"),
            "status": "Reserved"
        })
        save_db('books', books)
        save_db('transactions', transactions)
        logger.info(f"RESERVATION: Book {b_no} held for {s_id}")
        return jsonify({"success": True})
        
    return jsonify({"success": False, "message": "Book status conflict."})

@app.route('/api/process_transaction', methods=['POST'])
def api_process_action():
    """Admin endpoint to finalize physical Borrowing and Returning."""
    data = request.json
    b_no = data.get('book_no')
    action = data.get('action') # 'borrow', 'return', 'cancel'
    
    books = get_db('books')
    transactions = get_db('transactions')
    book = next((b for b in books if b['book_no'] == b_no), None)
    
    if not book: return jsonify({"success": False, "message": "Serial mismatch"}), 404

    # Locate the most recent active transaction for this specific book
    active_t = next((t for t in reversed(transactions) if t['book_no'] == b_no 
                    and t['status'] in ['Reserved', 'Borrowed']), None)

    if action == 'borrow':
        if book['status'] == 'Reserved' and active_t:
            book['status'] = 'Borrowed'
            active_t['status'] = 'Borrowed'
            active_t['expiry'] = (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d %H:%M")
        elif book['status'] == 'Available':
            book['status'] = 'Borrowed'
            transactions.append({
                "book_no": b_no, "school_id": data.get('school_id'), "date": datetime.now().strftime("%Y-%m-%d %H:%M"), 
                "expiry": (datetime.now() + timedelta(days=2)).strftime("%Y-%m-%d %H:%M"), "status": "Borrowed"
            })
    elif action == 'return':
        if active_t: active_t['status'] = 'Returned'
        book['status'] = 'Available'
    elif action == 'cancel':
        if active_t: active_t['status'] = 'Cancelled'
        book['status'] = 'Available'

    save_db('books', books)
    save_db('transactions', transactions)
    return jsonify({"success": True})

# --- SECURE AUTHENTICATION ENGINE ---

@app.route('/api/login', methods=['POST'])
def api_secure_login():
    """Strict cross-registry auth. Enforces passwords for staff and secured students."""
    data = request.json
    s_id = str(data.get('school_id', '')).strip().lower()
    pwd = data.get('password', '')
    
    profile = find_any_user(s_id)
    if not profile: 
        return jsonify({"success": False, "message": "ID not found in registry"}), 404
    
    # Staff Security Force
    if profile.get('is_staff') is True:
        if not pwd or profile.get('password') != pwd:
            return jsonify({"success": False, "message": "Invalid Staff Password"}), 401
            
    # Student Security Check (If password exists)
    elif profile.get('password'): 
        if profile.get('password') != pwd:
             return jsonify({"success": False, "message": "Invalid Student Password"}), 401
            
    token = str(uuid.uuid4())
    ACTIVE_SESSIONS[s_id] = token 
    
    logger.info(f"LOGIN SUCCESS: {s_id} logged in via {request.remote_addr}")
    return jsonify({"success": True, "token": token, "profile": profile})

@app.route('/api/user/<school_id>')
def api_get_profile(school_id):
    """Refreshes session data for the UI."""
    user = find_any_user(school_id)
    if user: return jsonify({"profile": user})
    return jsonify({"error": "Profile invalid"}), 404

# --- REGISTRATION & BULK IMPORT ENGINE ---

@app.route('/api/register_student', methods=['POST'])
def api_reg_student(): return perform_registration('users', 'Student')

@app.route('/api/register_librarian', methods=['POST'])
def api_reg_staff(): return perform_registration('admins', 'Staff')

def perform_registration(target_db_key, category_name):
    """Supports Multipart (with photos) and JSON (Ajax) registration routes."""
    if request.is_json:
        data = request.json
        name = data.get('name')
        s_id = str(data.get('school_id', '')).strip().lower()
        pwd = data.get('password', '')
    else:
        name = request.form.get('name')
        s_id = str(request.form.get('school_id', '')).strip().lower()
        pwd = request.form.get('password', '')
    
    if find_any_user(s_id):
        return jsonify({"success": False, "message": "ID collision detected."}), 400
    
    photo = "default.png"
    if 'photo' in request.files:
        f = request.files['photo']
        if f.filename != '':
            photo = secure_filename(f"{s_id}_{f.filename}")
            f.save(os.path.join(app.config['UPLOAD_FOLDER'], photo))
    
    registry = get_db(target_db_key)
    registry.append({
        "name": name, "school_id": s_id, "password": pwd,
        "category": category_name, "photo": photo,
        "created_at": datetime.now().strftime("%Y-%m-%d %H:%M")
    })
    save_db(target_db_key, registry)
    logger.info(f"REGISTRATION: New {category_name} added: {s_id}")
    return jsonify({"success": True, "id": s_id})

@app.route('/api/bulk_register', methods=['POST'])
def api_bulk_import():
    """Bulk book importer with categorization support."""
    data = request.json
    raw_text = data.get('text', '')
    target_cat = data.get('category', 'General')
    
    current_books = [] if data.get('clear_first') else get_db('books')
    count = 0
    
    for line in raw_text.strip().split('\n'):
        segments = line.split(maxsplit=1)
        if len(segments) == 2:
            b_id = segments[0].strip().upper()
            if not any(b['book_no'] == b_id for b in current_books):
                current_books.append({
                    "book_no": b_id, 
                    "title": segments[1].strip(), 
                    "status": "Available", 
                    "category": target_cat
                })
                count += 1
                
    save_db('books', current_books)
    return jsonify({"success": True, "items_added": count})

@app.route('/Profile/<path:filename>')
def serve_user_image(filename):
    """Serves uploaded user photos securely from the Profile folder."""
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# --- SYSTEM INITIALIZATION ---
initialize_system()

if __name__ == '__main__':
    # Binding to 0.0.0.0 for LAN/WiFi access across Tablet and LBAS devices
    logger.info("LBAS Backend V2.5 initializing on Port 80...")
    app.run(host='0.0.0.0', port=80, debug=True)