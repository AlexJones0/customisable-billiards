""" encryption module
Functions:
 - encrypt
 - decrypt
 - hash_text
 - compare_to_hashed
Classes:
  None.
Description:
  Contains basic functions related to encrypting and decrypting data as well as
hashing data and comparing hashes. Primarily used for basic obfuscaton and
security in order to protect insecure input data from being obtained, like a
user's password or email. Only simple enecryption is coded and the hashing uses
the SHA256 hashing algorithm with a salt."""

# external imports
import hashlib
import uuid


def encrypt(key, plaintext):
    """ Function created with help from https://stackoverflow.com/questions/2490334/simple-way-to-encode-a-string-according-to-a-password
        This method uses the Vigenère cipher to encrypt input plaintext data.
        This is not intended as a very secure encryption method but instead
        simple obfuscation to protect against basic attacks e.g. packet sniffing
          Inputs: key (a string with which the plaintext will be encrypted,
        ideally longer than the input plaintext), and plaintext (a string
        containing alphanumeric characters & symbols that is too be encrypted).
          Outputs: a string containing the encrypted unreadable ciphertext."""
    ciphertext = ""
    for char in range(len(plaintext)):
        # apply a caeser cipher shift based on the current key char
        ciphertext += chr(ord(plaintext[char])+ord(key[char % len(key)]) % 256)
        # modulo is used so that the key will match the length of the plaintext
    return ciphertext


def decrypt(key, ciphertext):
    """ Function created with help from https://stackoverflow.com/questions/2490334/simple-way-to-encode-a-string-according-to-a-password
        This method uses the Vigenère cipher to decrypt input ciphertext data.
        This is not intended as a very secure encryption method but instead
        simple obfuscation to protect against basic attacks e.g. packet sniffing
          Inputs: key (a string with which the plaintext will be decrypted, the
        same key used in the encryption), and ciphertext (a string containing
        alphanumeric characters and symbols that have been previously encrypted
        using the key).
          Outputs: a string containing the decrypted readable plaintext."""
    plaintext = ""
    for char in range(len(ciphertext)):
        # apply a caeser cipher shift backwards based on the current key char
        plaintext += chr(ord(ciphertext[char])-ord(key[char % len(key)]) % 256)
        # modulo is used so that the key will match the length of the plaintext
    return plaintext


def hash_text(text):
    """ Function created with help from https://www.pythoncentral.io/hashing-strings-with-python/
        This method hashes given text with the SHA256 algorithm so that
        sensitive data can be securely stored and compared.
          Inputs: text (a string containing informaton that will be hashed).
          Outputs: a string containing the hashed values in the format
        'hash_value:salt', where all of the characters in the hashed value and
        salt are hexadecimal."""
    salt = uuid.uuid4().hex  # generates random salt value
    hash_object = hashlib.sha256(salt.encode() + text.encode())
    hashed_string = hash_object.hexdigest()
    hashed_text = "{}:{}".format(hashed_string, salt)
    # we use : as a character because hashed_string only contains hex characters, and hence cannot contain colons.
    return hashed_text

def compare_to_hashed(text, hashed_text):
    """ Function created with help from https://www.pythoncentral.io/hashing-strings-with-python/
        This method compares given plain text with text that is already hashed
        in order to see if they are the same, validating the text. It does this
        by splitting the hashed text into the hashed value and the salt, and
        then applying the salt to the plain text and hashing it. If the same
        hash value is reached, the data is valid as the hashes are identical.
          Inputs: text (a string containing information to compare to the
        hashed value) and hashed_text (a string containing already hashed
        information in the form hash_value:salt to compare the plain text to).
          Outputs: a Boolean value describing whether the hashed values are an
        exact match or not."""
    hash_value, salt = hashed_text.split(":")
    hash_object = hashlib.sha256(salt.encode() + text.encode())
    # we hash the plain text for comparison with already hashed value
    new_hash_value = hash_object.hexdigest()
    return hash_value == new_hash_value
