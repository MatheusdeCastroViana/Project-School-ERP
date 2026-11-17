def mascarar_cpf(cpf):
    if not cpf:
        return ""
    digitos = "".join(c for c in cpf if c.isdigit())
    if len(digitos) != 11:
        return "***"
    return f"***.{digitos[3:6]}.{digitos[6:9]}-**"


def mascarar_telefone(telefone):
    if not telefone:
        return ""
    return "*" * max(len(telefone) - 4, 0) + telefone[-4:]