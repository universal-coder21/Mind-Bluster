from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
import os

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'dormmanagementkey123'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///dormitory.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# Initialize SQLAlchemy
db = SQLAlchemy(app)

# Create database models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='student')  # student, admin, staff
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=True)
    
    # Relationships
    complaints = db.relationship('Complaint', backref='user', lazy=True)
    maintenance_requests = db.relationship('MaintenanceRequest', backref='user', lazy=True)
    visitors = db.relationship('Visitor', backref='host', lazy=True)

class Room(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    room_number = db.Column(db.String(10), unique=True, nullable=False)
    capacity = db.Column(db.Integer, nullable=False, default=2)
    is_available = db.Column(db.Boolean, default=True)
    floor = db.Column(db.Integer, nullable=False)
    building = db.Column(db.String(50), nullable=False)
    
    # Relationships
    occupants = db.relationship('User', backref='room', lazy=True)
    room_requests = db.relationship('RoomRequest', backref='room', lazy=True)

class RoomRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    student_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey('room.id'), nullable=False)
    request_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, approved, rejected
    reason = db.Column(db.Text, nullable=True)
    
    # Relationship
    student = db.relationship('User', foreign_keys=[student_id])

class Complaint(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.Text, nullable=False)
    submission_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(20), nullable=False, default='open')  # open, in-progress, resolved
    resolution = db.Column(db.Text, nullable=True)
    resolution_date = db.Column(db.DateTime, nullable=True)

class MaintenanceRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    issue_type = db.Column(db.String(50), nullable=False)
    description = db.Column(db.Text, nullable=False)
    room_related = db.Column(db.Boolean, default=True)
    submission_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, in-progress, completed
    completion_date = db.Column(db.DateTime, nullable=True)

class Visitor(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    host_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    visitor_name = db.Column(db.String(100), nullable=False)
    purpose = db.Column(db.Text, nullable=False)
    check_in = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    check_out = db.Column(db.DateTime, nullable=True)
    id_number = db.Column(db.String(50), nullable=False)
    phone_number = db.Column(db.String(20), nullable=False)

class Notice(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    post_date = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    expiry_date = db.Column(db.DateTime, nullable=True)
    posted_by = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    is_active = db.Column(db.Boolean, default=True)
    
    # Relationship
    author = db.relationship('User', backref='notices')

# Create all tables
with app.app_context():
    db.create_all()
    
    # Create admin user if it doesn't exist
    admin_exists = User.query.filter_by(username='admin').first()
    if not admin_exists:
        admin = User(
            username='admin',
            password=generate_password_hash('admin123', method='pbkdf2:sha256'),
            email='admin@dorm.edu',
            full_name='Admin User',
            role='admin'
        )
        db.session.add(admin)
        db.session.commit()

# Authentication routes
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['role'] = user.role
            session['username'] = user.username
            flash('Login successful', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password', 'danger')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out', 'info')
    return redirect(url_for('login'))

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')
        full_name = request.form.get('full_name')
        
        # Check if username or email already exists
        existing_user = User.query.filter_by(username=username).first()
        existing_email = User.query.filter_by(email=email).first()
        
        if existing_user:
            flash('Username already exists', 'danger')
        elif existing_email:
            flash('Email already in use', 'danger')
        else:
            new_user = User(
                username=username,
                password=generate_password_hash(password, method='pbkdf2:sha256'),
                email=email,
                full_name=full_name,
                role='student'
            )
            db.session.add(new_user)
            db.session.commit()
            flash('Account created successfully! You can now login', 'success')
            return redirect(url_for('login'))
    
    return render_template('register.html')

# Dashboard route
@app.route('/')
@app.route('/dashboard')
def dashboard():
    if 'user_id' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    
    # Get notices
    notices = Notice.query.filter_by(is_active=True).order_by(Notice.post_date.desc()).limit(5).all()
    
    # For students
    if user.role == 'student':
        complaints = Complaint.query.filter_by(user_id=user.id).order_by(Complaint.submission_date.desc()).limit(5).all()
        maintenance_requests = MaintenanceRequest.query.filter_by(user_id=user.id).order_by(MaintenanceRequest.submission_date.desc()).limit(5).all()
        room_requests = RoomRequest.query.filter_by(student_id=user.id).order_by(RoomRequest.request_date.desc()).limit(5).all()
        visitors = Visitor.query.filter_by(host_id=user.id).order_by(Visitor.check_in.desc()).limit(5).all()
        
        return render_template('student_dashboard.html', 
                              user=user, 
                              notices=notices, 
                              complaints=complaints, 
                              maintenance_requests=maintenance_requests, 
                              room_requests=room_requests,
                              visitors=visitors)
    
    # For admin and staff
    else:
        # Get all pending requests for admin panel
        pending_room_requests = RoomRequest.query.filter_by(status='pending').count()
        open_complaints = Complaint.query.filter_by(status='open').count()
        pending_maintenance = MaintenanceRequest.query.filter_by(status='pending').count()
        active_visitors = Visitor.query.filter_by(check_out=None).count()
        
        return render_template('admin_dashboard.html', 
                              user=user, 
                              notices=notices, 
                              pending_room_requests=pending_room_requests,
                              open_complaints=open_complaints,
                              pending_maintenance=pending_maintenance,
                              active_visitors=active_visitors)

# Room management routes
@app.route('/rooms')
def view_rooms():
    if 'user_id' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))
    
    rooms = Room.query.all()
    return render_template('rooms.html', rooms=rooms)

@app.route('/room/request/<int:room_id>', methods=['GET', 'POST'])
def request_room(room_id):
    if 'user_id' not in session or session['role'] != 'student':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('dashboard'))
    
    room = Room.query.get_or_404(room_id)
    
    if request.method == 'POST':
        reason = request.form.get('reason')
        
        # Check if user already has a pending request for this room
        existing_request = RoomRequest.query.filter_by(
            student_id=session['user_id'],
            room_id=room_id,
            status='pending'
        ).first()
        
        if existing_request:
            flash('You already have a pending request for this room', 'warning')
        else:
            new_request = RoomRequest(
                student_id=session['user_id'],
                room_id=room_id,
                reason=reason
            )
            db.session.add(new_request)
            db.session.commit()
            flash('Room request submitted successfully', 'success')
            return redirect(url_for('view_rooms'))
    
    return render_template('request_room.html', room=room)

@app.route('/room/requests')
def manage_room_requests():
    if 'user_id' not in session or session['role'] not in ['admin', 'staff']:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('dashboard'))
    
    requests = RoomRequest.query.order_by(RoomRequest.request_date.desc()).all()
    return render_template('room_requests.html', requests=requests)

@app.route('/room/request/<int:request_id>/<action>')
def process_room_request(request_id, action):
    if 'user_id' not in session or session['role'] not in ['admin', 'staff']:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('dashboard'))
    
    room_request = RoomRequest.query.get_or_404(request_id)
    
    if action == 'approve':
        room_request.status = 'approved'
        
        # Assign room to student
        student = User.query.get(room_request.student_id)
        student.room_id = room_request.room_id
        
        # Update room availability if it's at capacity
        room = Room.query.get(room_request.room_id)
        occupants_count = User.query.filter_by(room_id=room.id).count()
        
        if occupants_count + 1 >= room.capacity:
            room.is_available = False
        
        flash('Room request approved', 'success')
    
    elif action == 'reject':
        room_request.status = 'rejected'
        flash('Room request rejected', 'success')
    
    db.session.commit()
    return redirect(url_for('manage_room_requests'))

@app.route('/room/add', methods=['GET', 'POST'])
def add_room():
    if 'user_id' not in session or session['role'] != 'admin':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        room_number = request.form.get('room_number')
        capacity = int(request.form.get('capacity'))
        floor = int(request.form.get('floor'))
        building = request.form.get('building')
        
        # Check if room already exists
        existing_room = Room.query.filter_by(room_number=room_number).first()
        
        if existing_room:
            flash('Room already exists', 'danger')
        else:
            new_room = Room(
                room_number=room_number,
                capacity=capacity,
                floor=floor,
                building=building
            )
            db.session.add(new_room)
            db.session.commit()
            flash('Room added successfully', 'success')
            return redirect(url_for('view_rooms'))
    
    return render_template('add_room.html')

# Complaint management routes
@app.route('/complaints')
def view_complaints():
    if 'user_id' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    
    if user.role == 'student':
        complaints = Complaint.query.filter_by(user_id=user.id).order_by(Complaint.submission_date.desc()).all()
    else:
        complaints = Complaint.query.order_by(Complaint.submission_date.desc()).all()
    
    return render_template('complaints.html', complaints=complaints)

@app.route('/complaint/new', methods=['GET', 'POST'])
def new_complaint():
    if 'user_id' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        
        new_complaint = Complaint(
            user_id=session['user_id'],
            title=title,
            description=description
        )
        db.session.add(new_complaint)
        db.session.commit()
        flash('Complaint submitted successfully', 'success')
        return redirect(url_for('view_complaints'))
    
    return render_template('new_complaint.html')

@app.route('/complaint/<int:complaint_id>')
def view_complaint(complaint_id):
    if 'user_id' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    complaint = Complaint.query.get_or_404(complaint_id)
    
    # Ensure student can only view their own complaints
    if user.role == 'student' and complaint.user_id != user.id:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('dashboard'))
    
    return render_template('view_complaint.html', complaint=complaint)

@app.route('/complaint/<int:complaint_id>/resolve', methods=['POST'])
def resolve_complaint(complaint_id):
    if 'user_id' not in session or session['role'] not in ['admin', 'staff']:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('dashboard'))
    
    complaint = Complaint.query.get_or_404(complaint_id)
    resolution = request.form.get('resolution')
    
    complaint.status = 'resolved'
    complaint.resolution = resolution
    complaint.resolution_date = datetime.utcnow()
    
    db.session.commit()
    flash('Complaint has been resolved', 'success')
    return redirect(url_for('view_complaints'))

@app.route('/complaint/<int:complaint_id>/update-status/<status>')
def update_complaint_status(complaint_id, status):
    if 'user_id' not in session or session['role'] not in ['admin', 'staff']:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('dashboard'))
    
    complaint = Complaint.query.get_or_404(complaint_id)
    
    if status in ['open', 'in-progress', 'resolved']:
        complaint.status = status
        db.session.commit()
        flash(f'Complaint status updated to {status}', 'success')
    
    return redirect(url_for('view_complaint', complaint_id=complaint_id))

# Maintenance request routes
@app.route('/maintenance')
def view_maintenance():
    if 'user_id' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    
    if user.role == 'student':
        requests = MaintenanceRequest.query.filter_by(user_id=user.id).order_by(MaintenanceRequest.submission_date.desc()).all()
    else:
        requests = MaintenanceRequest.query.order_by(MaintenanceRequest.submission_date.desc()).all()
    
    return render_template('maintenance.html', requests=requests)

@app.route('/maintenance/new', methods=['GET', 'POST'])
def new_maintenance():
    if 'user_id' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        issue_type = request.form.get('issue_type')
        description = request.form.get('description')
        room_related = True if request.form.get('room_related') == 'yes' else False
        
        new_request = MaintenanceRequest(
            user_id=session['user_id'],
            issue_type=issue_type,
            description=description,
            room_related=room_related
        )
        db.session.add(new_request)
        db.session.commit()
        flash('Maintenance request submitted successfully', 'success')
        return redirect(url_for('view_maintenance'))
    
    return render_template('new_maintenance.html')

@app.route('/maintenance/<int:request_id>/update/<status>')
def update_maintenance_status(request_id, status):
    if 'user_id' not in session or session['role'] not in ['admin', 'staff']:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('dashboard'))
    
    maintenance = MaintenanceRequest.query.get_or_404(request_id)
    
    if status in ['pending', 'in-progress', 'completed']:
        maintenance.status = status
        if status == 'completed':
            maintenance.completion_date = datetime.utcnow()
        db.session.commit()
        flash(f'Maintenance request status updated to {status}', 'success')
    
    return redirect(url_for('view_maintenance'))

# Visitor management routes
@app.route('/visitors')
def view_visitors():
    if 'user_id' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))
    
    user = User.query.get(session['user_id'])
    
    if user.role == 'student':
        visitors = Visitor.query.filter_by(host_id=user.id).order_by(Visitor.check_in.desc()).all()
    else:
        visitors = Visitor.query.order_by(Visitor.check_in.desc()).all()
    
    return render_template('visitors.html', visitors=visitors)

@app.route('/visitor/new', methods=['GET', 'POST'])
def new_visitor():
    if 'user_id' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        visitor_name = request.form.get('visitor_name')
        purpose = request.form.get('purpose')
        id_number = request.form.get('id_number')
        phone_number = request.form.get('phone_number')
        
        new_visitor = Visitor(
            host_id=session['user_id'],
            visitor_name=visitor_name,
            purpose=purpose,
            id_number=id_number,
            phone_number=phone_number
        )
        db.session.add(new_visitor)
        db.session.commit()
        flash('Visitor logged successfully', 'success')
        return redirect(url_for('view_visitors'))
    
    return render_template('new_visitor.html')

@app.route('/visitor/<int:visitor_id>/checkout')
def checkout_visitor(visitor_id):
    if 'user_id' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))
    
    visitor = Visitor.query.get_or_404(visitor_id)
    
    # Ensure only the host or admin/staff can check out visitors
    user = User.query.get(session['user_id'])
    if user.role == 'student' and visitor.host_id != user.id:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('dashboard'))
    
    visitor.check_out = datetime.utcnow()
    db.session.commit()
    flash('Visitor checked out successfully', 'success')
    return redirect(url_for('view_visitors'))

# Notice board routes
@app.route('/notices')
def view_notices():
    if 'user_id' not in session:
        flash('Please login first', 'warning')
        return redirect(url_for('login'))
    
    notices = Notice.query.filter_by(is_active=True).order_by(Notice.post_date.desc()).all()
    return render_template('notices.html', notices=notices)

@app.route('/notice/new', methods=['GET', 'POST'])
def new_notice():
    if 'user_id' not in session or session['role'] not in ['admin', 'staff']:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content')
        expiry_date = request.form.get('expiry_date')
        
        new_notice = Notice(
            title=title,
            content=content,
            posted_by=session['user_id']
        )
        
        if expiry_date:
            new_notice.expiry_date = datetime.strptime(expiry_date, '%Y-%m-%d')
        
        db.session.add(new_notice)
        db.session.commit()
        flash('Notice posted successfully', 'success')
        return redirect(url_for('view_notices'))
    
    return render_template('new_notice.html')

@app.route('/notice/<int:notice_id>/toggle')
def toggle_notice(notice_id):
    if 'user_id' not in session or session['role'] not in ['admin', 'staff']:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('dashboard'))
    
    notice = Notice.query.get_or_404(notice_id)
    notice.is_active = not notice.is_active
    db.session.commit()
    
    status = "activated" if notice.is_active else "deactivated"
    flash(f'Notice {status} successfully', 'success')
    return redirect(url_for('view_notices'))

# User management routes
@app.route('/users')
def manage_users():
    if 'user_id' not in session or session['role'] != 'admin':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('dashboard'))
    
    users = User.query.all()
    return render_template('users.html', users=users)

@app.route('/user/<int:user_id>/edit', methods=['GET', 'POST'])
def edit_user(user_id):
    if 'user_id' not in session or session['role'] != 'admin':
        flash('Unauthorized access', 'danger')
        return redirect(url_for('dashboard'))
    
    user = User.query.get_or_404(user_id)
    
    if request.method == 'POST':
        user.full_name = request.form.get('full_name')
        user.email = request.form.get('email')
        user.role = request.form.get('role')
        
        # Only update password if provided
        new_password = request.form.get('new_password')
        if new_password:
            user.password = generate_password_hash(new_password, method='pbkdf2:sha256')
        
        db.session.commit()
        flash('User updated successfully', 'success')
        return redirect(url_for('manage_users'))
    
    return render_template('edit_user.html', user=user)

# Helper route to check current room status
@app.route('/api/room-status')
def room_status():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401
    
    total_rooms = Room.query.count()
    occupied_rooms = Room.query.filter_by(is_available=False).count()
    available_rooms = total_rooms - occupied_rooms
    
    return jsonify({
        'total': total_rooms,
        'occupied': occupied_rooms,
        'available': available_rooms
    })

# Error handlers
@app.errorhandler(404)
def not_found(e):
    return render_template('404.html'), 404

@app.errorhandler(500)
def server_error(e):
    return render_template('500.html'), 500

# Run the app
if __name__ == '__main__':
    app.run(debug=True)