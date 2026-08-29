from django.contrib.auth.hashers import Argon2PasswordHasher

''' A OWASP diz que a configuração mínima do Argon2id é 19 MiB de memória, 
    uma contagem de iterações de 2 e 1 grau de paralelismo.'''

class UsuarioArgon2PasswordHasher(Argon2PasswordHasher):

    time_cost = 5
    memory_cost = 32768
    parallelism = 1