import os

# returns a password 13 characters long
def random_pass():
  return ''.join(map(lambda x:chr(ord(x) % 57 + 65), os.urandom(13)))
