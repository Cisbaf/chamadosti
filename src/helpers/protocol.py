from random import randint

def generate_protocol(size):
    protocol = "#"
    for _ in range(size):
        protocol += str(randint(1, 9))
    return protocol
