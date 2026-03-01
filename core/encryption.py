import os
import base64
import json
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

# In a real scenario, this key would be securely distributed.
# For demo purposes, we'll use a hardcoded 32-byte key.
# USP 5: Privacy-First Encrypted Processing
SHARED_KEY = b"amd_neural_grid_super_secret_key" # 32 bytes

def encrypt_payload(payload_dict: dict) -> str:
    """Encrypt a dictionary payload to a base64 string."""
    aesgcm = AESGCM(SHARED_KEY)
    nonce = os.urandom(12)
    
    data = json.dumps(payload_dict).encode('utf-8')
    ct = aesgcm.encrypt(nonce, data, None)
    
    print(f"🔐 Payload Encrypted | Nonce: {nonce.hex()} | Preview: {ct[:16].hex()}...")
    
    # Prepend nonce to ciphertext and base64 encode
    encrypted_blob = nonce + ct
    return base64.b64encode(encrypted_blob).decode('utf-8')

def decrypt_payload(encrypted_str: str) -> dict:
    """Decrypt a base64 string back to a dictionary."""
    aesgcm = AESGCM(SHARED_KEY)
    encrypted_blob = base64.b64decode(encrypted_str)
    
    nonce = encrypted_blob[:12]
    ct = encrypted_blob[12:]
    
    data = aesgcm.decrypt(nonce, ct, None)
    print("🔐 Auth Tag Verified successfully.")
    
    return json.loads(data.decode('utf-8'))
