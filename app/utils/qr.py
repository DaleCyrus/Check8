"""QR code generation and token verification utilities."""
import qrcode
import jwt
from datetime import datetime, timedelta
from typing import Optional
import io


def make_student_token(user) -> str:
    """
    Generate a JWT token containing student information.
    
    Args:
        user: User object with student information
        
    Returns:
        JWT token string
    """
    from ..extensions import db
    from ..models import User
    
    payload = {
        'user_id': user.id,
        'email': user.email,
        'student_number': getattr(user, 'student_number', None),
        'full_name': user.full_name,
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + timedelta(days=365),  # 1 year expiry
    }
    
    # Import from config
    from ..config import Config
    secret_key = Config.SECRET_KEY
    
    token = jwt.encode(payload, secret_key, algorithm='HS256')
    return token


def verify_student_token(token: str) -> Optional[dict]:
    """
    Verify and decode a JWT token.
    
    Args:
        token: JWT token string
        
    Returns:
        Decoded token payload or None if verification fails
    """
    try:
        from ..config import Config
        secret_key = Config.SECRET_KEY
        
        payload = jwt.decode(token, secret_key, algorithms=['HS256'])
        return payload
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None
    except Exception:
        return None


def token_to_png_bytes(token: str) -> bytes:
    """
    Generate a QR code PNG image from a token.
    
    Args:
        token: Token string to encode
        
    Returns:
        PNG image bytes
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_L,
        box_size=10,
        border=4,
    )
    qr.add_data(token)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Convert to bytes
    png_buffer = io.BytesIO()
    img.save(png_buffer, format='PNG')
    png_buffer.seek(0)
    
    return png_buffer.getvalue()
