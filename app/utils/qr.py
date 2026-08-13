"""QR code generation and token verification utilities."""
import qrcode
from datetime import datetime, timedelta
from typing import Optional
import io
import json
import base64


def make_student_token(user) -> str:
    """
    Generate a token containing student information (base64 encoded JSON).
    
    Args:
        user: User object with student information
        
    Returns:
        Base64 encoded token string
    """
    payload = {
        'user_id': user.id,
        'email': user.email,
        'student_number': getattr(user, 'student_number', None),
        'full_name': user.full_name,
        'iat': datetime.utcnow().isoformat(),
        'exp': (datetime.utcnow() + timedelta(days=365)).isoformat(),  # 1 year expiry
    }
    
    # Encode as JSON then base64
    json_str = json.dumps(payload)
    token = base64.b64encode(json_str.encode()).decode('utf-8')
    return token


def verify_student_token(token: str) -> Optional[dict]:
    """
    Verify and decode a base64 token.
    
    Args:
        token: Base64 encoded token string
        
    Returns:
        Decoded token payload or None if verification fails
    """
    try:
        # Decode from base64
        json_str = base64.b64decode(token).decode('utf-8')
        payload = json.loads(json_str)
        
        # Check expiry
        exp_str = payload.get('exp')
        if exp_str:
            exp_time = datetime.fromisoformat(exp_str)
            if datetime.utcnow() > exp_time:
                return None
        
        return payload
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
