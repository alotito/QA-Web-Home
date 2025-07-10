import hashlib

def hash_password(password):
    """Hashes the password using SHA256."""
    sha256 = hashlib.sha256()
    sha256.update(password.encode('utf-8'))
    return sha256.hexdigest()

# --- Use this script to get your hashed passwords ---
db_password = "InTheWhiteRoom!"
smtp_password = "SmtP!1354"

print(f"Hashed DB Password: {hash_password(db_password)}")
print(f"Hashed SMTP Password: {hash_password(smtp_password)}")