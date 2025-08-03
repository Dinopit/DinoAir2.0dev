#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Artifact Encryption Utilities
Provides field-level encryption/decryption for sensitive artifact data.
Uses AES-256 encryption with PBKDF2 key derivation.
"""

import base64
import json
import secrets
from typing import Dict, Any, List, Optional, Union
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.backends import default_backend


class ArtifactEncryption:
    """Handles field-level encryption for artifacts"""
    
    # Encryption parameters
    KEY_LENGTH = 32  # 256 bits for AES-256
    IV_LENGTH = 16   # 128 bits for AES block size
    SALT_LENGTH = 32  # 256 bits for salt
    ITERATIONS = 100000  # PBKDF2 iterations
    
    def __init__(self, password: Optional[str] = None):
        """
        Initialize encryption handler
        
        Args:
            password: User password for key derivation (optional)
        """
        self.password = password
        self._key_cache = {}
        
    def derive_key(self, password: str, salt: bytes) -> bytes:
        """
        Derive encryption key from password using PBKDF2
        
        Args:
            password: User password
            salt: Random salt for key derivation
            
        Returns:
            Derived encryption key
        """
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=self.KEY_LENGTH,
            salt=salt,
            iterations=self.ITERATIONS,
            backend=default_backend()
        )
        return kdf.derive(password.encode('utf-8'))
    
    def generate_salt(self) -> bytes:
        """Generate a random salt"""
        return secrets.token_bytes(self.SALT_LENGTH)
    
    def generate_iv(self) -> bytes:
        """Generate a random initialization vector"""
        return secrets.token_bytes(self.IV_LENGTH)
    
    def encrypt_data(self, data: Union[str, bytes], 
                     key: Optional[bytes] = None) -> Dict[str, str]:
        """
        Encrypt data using AES-256-CBC
        
        Args:
            data: Data to encrypt (string or bytes)
            key: Optional encryption key (will derive from password if not
                provided)
            
        Returns:
            Dictionary containing encrypted data, salt, and IV (all base64
            encoded)
        """
        # Convert string to bytes if necessary
        if isinstance(data, str):
            data = data.encode('utf-8')
            
        # Generate salt and derive key if not provided
        salt = self.generate_salt()
        if key is None:
            if not self.password:
                raise ValueError("No password provided for key derivation")
            key = self.derive_key(self.password, salt)
            
        # Generate IV and create cipher
        iv = self.generate_iv()
        cipher = Cipher(
            algorithms.AES(key),
            modes.CBC(iv),
            backend=default_backend()
        )
        encryptor = cipher.encryptor()
        
        # Pad data to block size (PKCS7 padding)
        block_size = 16  # AES block size
        padding_length = block_size - (len(data) % block_size)
        # Ensure data is bytes type for concatenation
        if not isinstance(data, bytes):
            data = bytes(data)
        padded_data = data + bytes([padding_length]) * padding_length
        
        # Encrypt
        encrypted = encryptor.update(padded_data) + encryptor.finalize()
        
        # Return base64 encoded values
        return {
            'data': base64.b64encode(encrypted).decode('utf-8'),
            'salt': base64.b64encode(salt).decode('utf-8'),
            'iv': base64.b64encode(iv).decode('utf-8')
        }
    
    def decrypt_data(self, encrypted_data: Dict[str, str], 
                     key: Optional[bytes] = None) -> bytes:
        """
        Decrypt data encrypted with encrypt_data
        
        Args:
            encrypted_data: Dictionary with encrypted data, salt, and IV
            key: Optional encryption key (will derive from password if not
                provided)
            
        Returns:
            Decrypted data as bytes
        """
        # Decode base64 values
        encrypted = base64.b64decode(encrypted_data['data'])
        salt = base64.b64decode(encrypted_data['salt'])
        iv = base64.b64decode(encrypted_data['iv'])
        
        # Derive key if not provided
        if key is None:
            if not self.password:
                raise ValueError("No password provided for key derivation")
            key = self.derive_key(self.password, salt)
            
        # Create cipher and decrypt
        cipher = Cipher(
            algorithms.AES(key),
            modes.CBC(iv),
            backend=default_backend()
        )
        decryptor = cipher.decryptor()
        decrypted_padded = decryptor.update(encrypted) + decryptor.finalize()
        
        # Remove PKCS7 padding
        padding_length = decrypted_padded[-1]
        decrypted = decrypted_padded[:-padding_length]
        
        return decrypted
    
    def encrypt_fields(self, data: Dict[str, Any], 
                       fields: List[str]) -> Dict[str, Any]:
        """
        Encrypt specific fields in a dictionary
        
        Args:
            data: Dictionary containing data
            fields: List of field names to encrypt
            
        Returns:
            Dictionary with specified fields encrypted
        """
        encrypted_data = data.copy()
        encrypted_fields_info = {}
        
        for field in fields:
            if field in data and data[field] is not None:
                # Convert value to string for encryption
                value = json.dumps(data[field]) if not isinstance(
                    data[field], str) else data[field]
                
                # Encrypt the field
                encrypted_info = self.encrypt_data(value)
                
                # Store encrypted value
                encrypted_data[field] = encrypted_info['data']
                
                # Store encryption info (salt and IV) separately
                encrypted_fields_info[field] = {
                    'salt': encrypted_info['salt'],
                    'iv': encrypted_info['iv']
                }
        
        # Add encryption metadata
        if encrypted_fields_info:
            encrypted_data['_encryption_info'] = encrypted_fields_info
            
        return encrypted_data
    
    def decrypt_fields(self, data: Dict[str, Any], 
                       fields: List[str]) -> Dict[str, Any]:
        """
        Decrypt specific fields in a dictionary
        
        Args:
            data: Dictionary containing encrypted data
            fields: List of field names to decrypt
            
        Returns:
            Dictionary with specified fields decrypted
        """
        decrypted_data = data.copy()
        encryption_info = data.get('_encryption_info', {})
        
        for field in fields:
            if field in data and field in encryption_info:
                # Reconstruct encrypted data dictionary
                encrypted_dict = {
                    'data': data[field],
                    'salt': encryption_info[field]['salt'],
                    'iv': encryption_info[field]['iv']
                }
                
                # Decrypt
                decrypted_bytes = self.decrypt_data(encrypted_dict)
                decrypted_str = decrypted_bytes.decode('utf-8')
                
                # Try to parse as JSON (for complex types)
                try:
                    decrypted_value = json.loads(decrypted_str)
                except json.JSONDecodeError:
                    decrypted_value = decrypted_str
                    
                decrypted_data[field] = decrypted_value
        
        # Remove encryption metadata
        if '_encryption_info' in decrypted_data:
            del decrypted_data['_encryption_info']
            
        return decrypted_data
    
    def encrypt_artifact_fields(self, artifact_dict: Dict[str, Any], 
                                fields: List[str]) -> Dict[str, Any]:
        """
        Encrypt specific fields in an artifact dictionary
        
        Args:
            artifact_dict: Artifact data as dictionary
            fields: List of field names to encrypt
            
        Returns:
            Artifact dictionary with specified fields encrypted
        """
        # Encrypt the specified fields
        encrypted_dict = self.encrypt_fields(artifact_dict, fields)
        
        # Update encrypted_fields list
        encrypted_dict['encrypted_fields'] = ','.join(fields)
        
        return encrypted_dict
    
    def decrypt_artifact_fields(
            self,
            artifact_dict: Dict[str, Any]) -> Dict[str, Any]:
        """
        Decrypt encrypted fields in an artifact dictionary
        
        Args:
            artifact_dict: Artifact data with encrypted fields
            
        Returns:
            Artifact dictionary with fields decrypted
        """
        # Get list of encrypted fields
        encrypted_fields_str = artifact_dict.get('encrypted_fields', '')
        if not encrypted_fields_str:
            return artifact_dict
            
        encrypted_fields = [f.strip() for f in encrypted_fields_str.split(',')]
        
        # Decrypt the fields
        decrypted_dict = self.decrypt_fields(artifact_dict, encrypted_fields)
        
        return decrypted_dict
    
    def generate_encryption_key_id(self) -> str:
        """Generate a unique encryption key ID"""
        return base64.urlsafe_b64encode(
            secrets.token_bytes(16)).decode('utf-8').rstrip('=')
    
    def rotate_encryption(self, data: Dict[str, Any], 
                          old_password: str, 
                          new_password: str,
                          fields: List[str]) -> Dict[str, Any]:
        """
        Re-encrypt data with a new password
        
        Args:
            data: Dictionary containing encrypted data
            old_password: Current password
            new_password: New password  
            fields: List of encrypted field names
            
        Returns:
            Dictionary with fields re-encrypted using new password
        """
        # Create temporary decryption instance with old password
        old_encryptor = ArtifactEncryption(old_password)
        
        # Decrypt with old password
        decrypted_data = old_encryptor.decrypt_fields(data, fields)
        
        # Create new encryption instance with new password
        new_encryptor = ArtifactEncryption(new_password)
        
        # Re-encrypt with new password
        return new_encryptor.encrypt_fields(decrypted_data, fields)


# Convenience functions for simple encryption/decryption
def encrypt_text(text: str, password: str) -> str:
    """
    Simple text encryption
    
    Args:
        text: Text to encrypt
        password: Password for encryption
        
    Returns:
        Base64 encoded encrypted data with metadata
    """
    encryptor = ArtifactEncryption(password)
    encrypted = encryptor.encrypt_data(text)
    
    # Combine all parts into a single string
    combined = json.dumps(encrypted)
    return base64.b64encode(combined.encode('utf-8')).decode('utf-8')


def decrypt_text(encrypted_text: str, password: str) -> str:
    """
    Simple text decryption
    
    Args:
        encrypted_text: Base64 encoded encrypted data
        password: Password for decryption
        
    Returns:
        Decrypted text
    """
    # Decode and parse
    combined = base64.b64decode(encrypted_text).decode('utf-8')
    encrypted_data = json.loads(combined)
    
    # Decrypt
    encryptor = ArtifactEncryption(password)
    decrypted_bytes = encryptor.decrypt_data(encrypted_data)
    
    return decrypted_bytes.decode('utf-8')


# Example usage and testing
if __name__ == "__main__":
    # Test basic encryption/decryption
    password = "test_password_123"
    encryptor = ArtifactEncryption(password)
    
    # Test data encryption
    test_data = "This is sensitive data!"
    encrypted = encryptor.encrypt_data(test_data)
    print(f"Encrypted: {encrypted}")
    
    decrypted = encryptor.decrypt_data(encrypted)
    print(f"Decrypted: {decrypted.decode('utf-8')}")
    
    # Test field encryption
    artifact_data = {
        "id": "123",
        "name": "Test Artifact",
        "content": "Sensitive content here",
        "description": "Public description",
        "metadata": {"secret": "value", "public": "info"}
    }
    
    fields_to_encrypt = ["content", "metadata"]
    encrypted_artifact = encryptor.encrypt_artifact_fields(
        artifact_data, fields_to_encrypt)
    print(f"\nEncrypted artifact: {json.dumps(encrypted_artifact, indent=2)}")
    
    decrypted_artifact = encryptor.decrypt_artifact_fields(encrypted_artifact)
    print(f"\nDecrypted artifact: {json.dumps(decrypted_artifact, indent=2)}")
    
    # Test simple functions
    simple_encrypted = encrypt_text("Simple secret", password)
    print(f"\nSimple encrypted: {simple_encrypted}")
    
    simple_decrypted = decrypt_text(simple_encrypted, password)
    print(f"Simple decrypted: {simple_decrypted}")