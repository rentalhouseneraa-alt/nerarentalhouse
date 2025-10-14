from app import create_app, db
from app.models import User

app = create_app()
app.app_context().push()

# Create admin user
u = User(username='admin', full_name='Super Admin', is_admin=True)
u.set_password('admin123')  # Change this password after first login

db.session.add(u)
db.session.commit()

print("✅ Admin user created successfully! (username='admin', password='admin123')")
