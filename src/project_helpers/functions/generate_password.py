import hashlib
import string
import random
import os
import binascii


def generate_password(length):
    source = string.ascii_letters + string.digits + string.punctuation
    source.replace("\\", "")

    password = random.choice(string.ascii_lowercase)
    password += random.choice(string.ascii_uppercase)
    password += random.choice(string.digits)
    password += random.choice(string.punctuation)

    for i in range(length - 4):
        password += random.choice(source)

    password_list = list(password)
    random.SystemRandom().shuffle(password_list)

    password_str = ''.join(password_list)
    password_str = password_str.replace("\\", "*")

    return password_str


def hash_password(password):
    salt = hashlib.sha256(os.urandom(60)).hexdigest().encode('ascii')
    hashed_password = hashlib.pbkdf2_hmac('sha512', password.encode('utf-8'),
                                          salt, 100000)
    hashed_password = binascii.hexlify(hashed_password)
    return (salt + hashed_password).decode('ascii')


def verify_password(stored_password, provided_password):
    salt = stored_password[:64]
    stored_password = stored_password[64:]
    hashed_password = hashlib.pbkdf2_hmac('sha512', provided_password.encode('utf-8'), salt.encode('ascii'), 100000)
    hashed_password = binascii.hexlify(hashed_password).decode('ascii')
    return hashed_password == stored_password