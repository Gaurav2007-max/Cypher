import sys
import argparse
from app import create_app
from app.extensions import db
from app.models.user import User, UserProfile

def create_or_promote_admin(username, email, password):
    app = create_app()
    with app.app_context():
        user = User.query.filter((User.username == username) | (User.email == email)).first()
        if user:
            print(f"User '{user.username}' already exists. Promoting to Administrator...")
            user.role = 'admin'
            user.authority_approved = True
            if password:
                user.set_password(password)
            db.session.commit()
            print(f"Success: '{user.username}' is now an Administrator.")
            return

        print(f"Creating new Administrator: {username} ({email})...")
        new_admin = User(
            username=username,
            email=email,
            role='admin',
            authority_approved=True
        )
        new_admin.set_password(password)
        db.session.add(new_admin)
        db.session.flush()

        profile = UserProfile(
            user_id=new_admin.id,
            full_name=username.capitalize(),
            emergency_consent=False
        )
        db.session.add(profile)
        db.session.commit()
        print(f"Success: Administrator '{username}' created successfully!")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Create or promote an Administrator account in TravelTech.")
    parser.add_argument('--username', default='admin', help="Admin username (default: admin)")
    parser.add_argument('--email', default='admin@traveltech.local', help="Admin email")
    parser.add_argument('--password', required=True, help="Set a unique administrator password.")

    args = parser.parse_args()
    create_or_promote_admin(args.username, args.email, args.password)
