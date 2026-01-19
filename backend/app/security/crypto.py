"""Encryption and data security utilities."""

import os
import base64
from typing import Optional
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2


class CryptoUtil:
    """Encryption and decryption utilities."""
    
    def __init__(self, secret_key: Optional[str] = None):
        """
        Initialize crypto utility.
        
        Args:
            secret_key: Base64-encoded secret key, or None to generate from env
        """
        if secret_key is None:
            # Try to get from environment, or generate new
            env_key = os.getenv("ENCRYPTION_KEY")
            if env_key:
                secret_key = env_key
            else:
                # Generate a new key
                secret_key = Fernet.generate_key().decode()
        
        if isinstance(secret_key, str):
            secret_key = secret_key.encode()
        
        # If key is not properly base64 encoded, derive it
        if len(secret_key) != 44:  # Fernet keys are 44 bytes when encoded
            # Derive key from secret
            self.key = self._derive_key(secret_key)
        else:
            self.key = secret_key
        
        self.cipher = Fernet(self.key)
    
    @staticmethod
    def _derive_key(secret: bytes, salt: bytes = b"ddas_salt") -> bytes:
        """Derive encryption key from secret."""
        kdf = PBKDF2(
            algorithm=hashes.SHA256(),
            length=32,
            salt=salt,
            iterations=100000,
        )
        key = base64.urlsafe_b64encode(kdf.derive(secret))
        return key
    
    def encrypt(self, plaintext: str) -> str:
        """
        Encrypt plaintext.
        
        Args:
            plaintext: Text to encrypt
        
        Returns:
            Base64-encoded encrypted text
        """
        if isinstance(plaintext, str):
            plaintext = plaintext.encode()
        
        encrypted = self.cipher.encrypt(plaintext)
        return base64.b64encode(encrypted).decode()
    
    def decrypt(self, encrypted_text: str) -> str:
        """
        Decrypt encrypted text.
        
        Args:
            encrypted_text: Base64-encoded encrypted text
        
        Returns:
            Decrypted plaintext
        """
        if isinstance(encrypted_text, str):
            encrypted_text = encrypted_text.encode()
        
        encrypted_bytes = base64.b64decode(encrypted_text)
        decrypted = self.cipher.decrypt(encrypted_bytes)
        return decrypted.decode()
    
    @staticmethod
    def generate_key() -> str:
        """Generate a new Fernet key."""
        return Fernet.generate_key().decode()


class FieldEncryption:
    """Encrypt/decrypt database fields."""
    
    def __init__(self, crypto: Optional[CryptoUtil] = None):
        self.crypto = crypto or CryptoUtil()
    
    def encrypt_field(self, value: str) -> str:
        """Encrypt a field value."""
        if not value:
            return ""
        return self.crypto.encrypt(value)
    
    def decrypt_field(self, encrypted_value: str) -> str:
        """Decrypt a field value."""
        if not encrypted_value:
            return ""
        try:
            return self.crypto.decrypt(encrypted_value)
        except Exception:
            # Return empty if decryption fails
            return ""


# Global crypto instance
crypto = CryptoUtil()
