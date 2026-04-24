from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Book',
            fields=[
                ('book_no', models.CharField(max_length=50, primary_key=True, serialize=False, unique=True)),
                ('title', models.CharField(max_length=255)),
                ('author', models.CharField(blank=True, max_length=150)),
                ('category', models.CharField(default='General', max_length=80)),
                ('status', models.CharField(choices=[('Available', 'Available'), ('Pending', 'Pending'), ('Reserved', 'Reserved'), ('Borrowed', 'Borrowed'), ('Unreturned', 'Unreturned')], default='Available', max_length=30)),
            ],
            options={
                'db_table': 'lbas_books',
            },
        ),
        migrations.CreateModel(
            name='Category',
            fields=[
                ('name', models.CharField(max_length=100, primary_key=True, serialize=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'lbas_categories',
            },
        ),
        migrations.CreateModel(
            name='Course',
            fields=[
                ('name', models.CharField(max_length=100, primary_key=True, serialize=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'lbas_courses',
            },
        ),
        migrations.CreateModel(
            name='DateRestriction',
            fields=[
                ('date', models.DateField(primary_key=True, serialize=False, unique=True)),
                ('action', models.CharField(choices=[('ban', 'Ban'), ('lift', 'Lift')], max_length=10)),
                ('reason', models.TextField(blank=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'lbas_date_restrictions',
            },
        ),
        migrations.CreateModel(
            name='UserProfile',
            fields=[
                ('school_id', models.CharField(max_length=50, primary_key=True, serialize=False, unique=True)),
                ('name', models.CharField(max_length=150)),
                ('password', models.CharField(max_length=255)),
                ('is_staff', models.BooleanField(default=False)),
                ('status', models.CharField(choices=[('approved', 'Approved'), ('pending', 'Pending'), ('rejected', 'Rejected'), ('expired', 'Expired')], default='approved', max_length=20)),
                ('category', models.CharField(choices=[('College Student', 'College Student'), ('High School Student', 'High School Student'), ('Staff', 'Staff')], max_length=50)),
                ('school_level', models.CharField(choices=[('College', 'College'), ('High School', 'High School')], max_length=20)),
                ('year_level', models.CharField(choices=[('Grade 7', 'Grade 7'), ('Grade 8', 'Grade 8'), ('Grade 9', 'Grade 9'), ('Grade 10', 'Grade 10'), ('1st Year', '1st Year'), ('2nd Year', '2nd Year'), ('3rd Year', '3rd Year'), ('4th Year', '4th Year')], max_length=20)),
                ('course', models.CharField(blank=True, max_length=100)),
                ('phone_number', models.CharField(blank=True, max_length=20)),
                ('email', models.CharField(blank=True, max_length=150)),
                ('photo', models.CharField(default='avatar_fox.svg', max_length=255)),
                ('account_expires_at', models.DateTimeField(blank=True, null=True)),
                ('expiry_notified', models.BooleanField(default=False)),
                ('account_status_detail', models.CharField(choices=[('active', 'Active'), ('expiry_warned', 'Expiry Warned'), ('expired', 'Expired')], default='active', max_length=30)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'lbas_users',
            },
        ),
        migrations.CreateModel(
            name='Transaction',
            fields=[
                ('transaction_id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('book_no', models.CharField(max_length=50)),
                ('book_title', models.CharField(max_length=255)),
                ('student_id', models.CharField(max_length=50)),
                ('student_name', models.CharField(max_length=150)),
                ('status', models.CharField(choices=[('Pending', 'Pending'), ('Reserved', 'Reserved'), ('Borrowed', 'Borrowed'), ('Returned', 'Returned'), ('Cancelled', 'Cancelled'), ('Expired', 'Expired'), ('Unavailable', 'Unavailable'), ('Unreturned', 'Unreturned')], default='Pending', max_length=30)),
                ('date_reserved', models.DateTimeField(auto_now_add=True)),
                ('is_approved', models.BooleanField(default=False)),
                ('approved_by', models.CharField(blank=True, max_length=50)),
                ('approved_by_name', models.CharField(blank=True, max_length=150)),
                ('date_approved', models.DateTimeField(blank=True, null=True)),
                ('pickup_deadline', models.DateTimeField(blank=True, null=True)),
                ('pending_expires_at', models.DateTimeField(blank=True, null=True)),
                ('date_borrowed', models.DateTimeField(blank=True, null=True)),
                ('return_due_date', models.DateTimeField(blank=True, null=True)),
                ('date_returned', models.DateTimeField(blank=True, null=True)),
                ('reservation_note', models.TextField(blank=True)),
                ('pickup_location', models.CharField(blank=True, max_length=100)),
                ('queue_position', models.IntegerField(default=1)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'db_table': 'lbas_transactions',
            },
        ),
        migrations.CreateModel(
            name='Session',
            fields=[
                ('token', models.CharField(max_length=100, primary_key=True, serialize=False, unique=True)),
                ('school_id', models.CharField(max_length=50)),
                ('is_staff', models.BooleanField(default=False)),
                ('expires_at', models.DateTimeField()),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'lbas_sessions',
            },
        ),
        migrations.CreateModel(
            name='RegistrationRequest',
            fields=[
                ('request_id', models.CharField(max_length=100, primary_key=True, serialize=False, unique=True)),
                ('request_number', models.CharField(max_length=10)),
                ('name', models.CharField(max_length=150)),
                ('school_id', models.CharField(max_length=50)),
                ('password', models.CharField(max_length=255)),
                ('year_level', models.CharField(max_length=20)),
                ('school_level', models.CharField(max_length=20)),
                ('category', models.CharField(max_length=50)),
                ('course', models.CharField(blank=True, max_length=100)),
                ('phone_number', models.CharField(blank=True, max_length=20)),
                ('email', models.CharField(blank=True, max_length=150)),
                ('photo', models.CharField(default='avatar_fox.svg', max_length=255)),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending', max_length=20)),
                ('reviewed_by', models.CharField(blank=True, max_length=50)),
                ('reviewed_at', models.DateTimeField(blank=True, null=True)),
                ('pending_expires_at', models.DateTimeField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'lbas_registration_requests',
            },
        ),
        migrations.CreateModel(
            name='Notification',
            fields=[
                ('notification_id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('recipient_school_id', models.CharField(max_length=50)),
                ('notification_type', models.CharField(choices=[('reservation_pending', 'Reservation Pending'), ('reservation_approved', 'Reservation Approved'), ('borrow_activated', 'Borrow Activated'), ('overdue_reminder', 'Overdue Reminder'), ('registration_approved', 'Registration Approved'), ('reservation_expired', 'Reservation Expired'), ('account_expiry_warning', 'Account Expiry Warning'), ('account_expired', 'Account Expired')], max_length=50)),
                ('title', models.CharField(max_length=255)),
                ('message', models.TextField()),
                ('related_transaction_id', models.UUIDField(blank=True, null=True)),
                ('related_book_no', models.CharField(blank=True, max_length=50)),
                ('sent_by', models.CharField(blank=True, max_length=50)),
                ('is_read', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
            options={
                'db_table': 'lbas_notifications',
            },
        ),
    ]
