#!/usr/bin/env python3
"""Generate a password hash for the CMS admin user.
Usage: python3 generate_hash.py
"""
import getpass
import secrets
import hashlib

password = getpass.getpass("Enter admin password: ")
confirm = getpass.getpass("Confirm password: ")

if password != confirm:
    print("Passwords don't match!")
    exit(1)

salt = secrets.token_hex(16)
hashed = hashlib.sha256(f"{salt}:{password}".encode()).hexdigest()
print(f"\nYour ADMIN_PASSWORD_HASH:\n{salt}:{hashed}")
print("\nAdd this to /opt/portfolio/.env")
