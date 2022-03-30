import hashlib
print(hashlib.sha256('block_string'.encode()).hexdigest())
print(len(hashlib.sha256('block_string'.encode()).hexdigest()))