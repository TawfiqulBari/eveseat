"""
Token encryption utilities using Fernet
"""
from cryptography.fernet import Fernet
from app.core.config import settings
import base64
import hashlib
import logging

logger = logging.getLogger(__name__)


class TokenEncryption:
    """
    Handles encryption and decryption of sensitive tokens using Fernet
    """
    
    def __init__(self, encryption_key: str = None):
        """
        Initialize encryption with a key
        
        Args:
            encryption_key: Base64-encoded Fernet key. If None, uses ENCRYPTION_KEY from settings.
        """
        key = encryption_key or settings.ENCRYPTION_KEY
        
        # If key is not base64-encoded, derive a key from it
        if not self._is_base64(key):
            key = self._derive_key(key)
        
        try:
            self.cipher = Fernet(key.encode() if isinstance(key, str) else key)
        except Exception as e:
            logger.error(f"Failed to initialize encryption: {e}")
            raise ValueError(f"Invalid encryption key: {e}")
    
    @staticmethod
    def _is_base64(s: str) -> bool:
        """Check if string is base64-encoded"""
        try:
            if isinstance(s, bytes):
                s = s.decode()
            base64.b64decode(s, validate=True)
            return True
        except Exception:
            return False
    
    @staticmethod
    def _derive_key(password: str) -> str:
        """
        Derive a Fernet key from a password using SHA256
        
        Note: In production, use a proper key derivation function like PBKDF2
        """
        # Hash the password to get 32 bytes
        key = hashlib.sha256(password.encode()).digest()
        # Encode to base64 for Fernet
        return base64.urlsafe_b64encode(key).decode()
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt a plaintext string
        
        Args:
            plaintext: String to encrypt
            
        Returns:
            Base64-encoded encrypted string
        """
        try:
            encrypted = self.cipher.encrypt(plaintext.encode())
            return encrypted.decode()
        except Exception as e:
            logger.error(f"Encryption failed: {e}")
            raise
    
    def decrypt(self, ciphertext: str) -> str:
        """
        Decrypt an encrypted string
        
        Args:
            ciphertext: Base64-encoded encrypted string
            
        Returns:
            Decrypted plaintext string
        """
        try:
            decrypted = self.cipher.decrypt(ciphertext.encode())
            return decrypted.decode()
        except Exception as e:
            logger.error(f"Decryption failed: {e}")
            raise


# Global instance
encryption = TokenEncryption()

