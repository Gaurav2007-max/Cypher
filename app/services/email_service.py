import smtplib
from email.utils import parseaddr
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from flask import current_app

class EmailService:
    @staticmethod
    def send_contact_verification(contact, verification_url):
        config = current_app.config
        if config.get('SMTP_TEST_MODE', True):
            return {'success': False, 'mode': 'test_mode', 'note': 'No verification email was sent in test mode.'}

        username = config.get('SMTP_USERNAME')
        password = config.get('SMTP_PASSWORD')
        if not username or not password:
            return {'success': False, 'mode': 'smtp_not_configured', 'error': 'SMTP credentials are not configured.'}

        message = MIMEText(
            f"Verify this emergency contact email by opening this link:\n\n{verification_url}\n\n"
            "The link expires in 30 minutes. If you did not request this, ignore this message."
        )
        message['From'] = config.get('SMTP_DEFAULT_SENDER') or username
        if parseaddr(message['From'])[1].endswith('@traveltech.local'):
            message['From'] = username
        message['To'] = contact.email
        message['Subject'] = 'Verify your TravelTech emergency contact email'
        try:
            with smtplib.SMTP(config.get('SMTP_SERVER'), config.get('SMTP_PORT'), timeout=10) as server:
                if config.get('SMTP_USE_TLS'):
                    server.starttls()
                server.login(username, password)
                server.send_message(message)
            return {'success': True, 'mode': 'live_smtp'}
        except (smtplib.SMTPException, OSError, ValueError) as error:
            current_app.logger.error('Failed to send emergency-contact verification email: %s', error)
            return {'success': False, 'mode': 'live_smtp_failed', 'error': str(error)}

    @staticmethod
    def send_emergency_alert(user, emergency_contact, incident_type, latitude=None, longitude=None, accuracy=None, location_trail=None):
        """
        Prepares and sends an emergency SOS alert via SMTP.
        Includes a safe Test Mode that simulates email delivery without needing live SMTP credentials.
        """
        config = current_app.config
        test_mode = config.get('SMTP_TEST_MODE', True)
        recipient = emergency_contact.email if emergency_contact else None

        if not recipient:
            return {
                'success': False,
                'mode': 'no_recipient',
                'error': 'No emergency contact email registered for this account.'
            }

        if not test_mode and not (
            emergency_contact.verification and emergency_contact.verification.is_verified
        ):
            return {
                'success': False,
                'mode': 'contact_not_verified',
                'recipient': recipient,
                'error': 'The emergency contact email must be verified before live alerts can be sent.'
            }

        now_str = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S UTC')
        incident_titles = {
            'sos_manual': '🚨 URGENT: Manual SOS Alert Activated',
            'fall_detected': '⚠️ URGENT: Potential Fall Incident Detected',
            'checkin_expired': '⏰ URGENT: Safety Check-in Timer Expired'
        }
        subject = f"[TravelTech Safety Alert] {incident_titles.get(incident_type, 'Emergency Alert')} for {user.username}"

        # Construct location info
        has_location = latitude is not None and longitude is not None
        map_link = f"https://www.google.com/maps?q={latitude},{longitude}" if has_location else "Not available (location permission not granted)"
        coords_str = f"{latitude:.6f}, {longitude:.6f} (accuracy ±{accuracy or 20}m)" if has_location else "Unknown Coordinates"

        trail_info = ""
        if location_trail and isinstance(location_trail, list) and len(location_trail) > 0:
            trail_info = "\n\nRecent 10-Minute Breadcrumb Trail (Last Known Coordinates):\n"
            for idx, pt in enumerate(location_trail[-5:], 1):
                trail_info += f"  {idx}. Lat: {pt.get('latitude', 'N/A')}, Lng: {pt.get('longitude', 'N/A')} at {pt.get('recorded_at', 'N/A')}\n"

        body = f"""EMERGENCY ALERT NOTIFICATION
==================================================
Tourist Username: {user.username}
User Email: {user.email}
Emergency Contact: {emergency_contact.name} ({emergency_contact.relationship or 'Emergency Contact'})
Contact Type: {'Registered Travel Agency / Consulate' if emergency_contact.is_agency else 'Personal Emergency Contact'}
Incident Time: {now_str}
Incident Type: {incident_type}

CURRENT LOCATION:
Coordinates: {coords_str}
Interactive Map: {map_link}
{trail_info}
IMPORTANT NOTE:
The tourist triggered an emergency notification through TravelTech Tourist Safety Platform.
If you are unable to reach the traveler, please contact local tourist helpline or emergency authorities in their destination city.

TravelTech Platform Security & Safety System
==================================================
"""

        if test_mode:
            current_app.logger.info(f"[TEST MODE EMAIL] To: {recipient} | Subject: {subject}\n{body}")
            return {
                'success': False,
                'mode': 'test_mode',
                'recipient': recipient,
                'subject': subject,
                'note': 'The SOS incident was recorded, but no email was sent because SMTP test mode is enabled.'
            }

        username = config.get('SMTP_USERNAME')
        password = config.get('SMTP_PASSWORD')
        if not username or not password:
            current_app.logger.error('Live SOS email is not configured: SMTP username or password is missing.')
            return {
                'success': False,
                'mode': 'smtp_not_configured',
                'recipient': recipient,
                'error': 'Live email is not configured. Set SMTP_TEST_MODE=False and provide SMTP credentials.'
            }

        try:
            msg = MIMEMultipart()
            sender = config.get('SMTP_DEFAULT_SENDER') or username
            sender_address = parseaddr(sender)[1]
            if sender_address.endswith('@traveltech.local'):
                sender = username
            msg['From'] = sender
            msg['To'] = recipient
            msg['Subject'] = subject
            msg.attach(MIMEText(body, 'plain'))

            with smtplib.SMTP(config.get('SMTP_SERVER'), config.get('SMTP_PORT'), timeout=10) as server:
                if config.get('SMTP_USE_TLS'):
                    server.starttls()
                server.login(username, password)
                server.send_message(msg)

            return {
                'success': True,
                'mode': 'live_smtp',
                'recipient': recipient,
                'subject': subject
            }
        except (smtplib.SMTPException, OSError, ValueError) as e:
            current_app.logger.error(f"Failed to send emergency email via SMTP: {str(e)}")
            return {
                'success': False,
                'mode': 'live_smtp_failed',
                'error': str(e),
                'recipient': recipient
            }
