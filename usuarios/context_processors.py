import unicodedata


def _normalizar(texto):
    """Remove acentos e deixa minúsculo, pra comparar 'Gestão' com 'gestao'."""
    if not texto:
        return ""
    sem_acento = unicodedata.normalize('NFKD', texto).encode('ASCII', 'ignore').decode('ASCII')
    return sem_acento.lower()


def menu_lateral(request):
    if not request.user.is_authenticated:
        return {"menu_lateral": [], "setor_usuario": None}

    usuario = request.user
    funcionario = getattr(usuario, 'funcionario', None)
    cargo = funcionario.cargo if funcionario else None
    setor_usuario_id = _normalizar(cargo.setor.nome) if cargo and cargo.setor else None

    itens_completos = [
        {
            "id": "administrador",
            "rotulo": "Administrador",
            "url": "/admin/",
            "icone": "administrador",
            "somente_staff": True,
        },
        {
            "id": "gestao",
            "rotulo": "Gestão",
            "url": "#",  # TODO: trocar por {% url 'gestao:home' %} quando o app existir
            "icone": "gestao",
            "somente_staff": False,
        },
        {
            "id": "pedagogico",
            "rotulo": "Pedagógico",
            "url": "#",  # TODO: trocar por {% url 'pedagogico:home' %} quando o app existir
            "icone": "pedagogico",
            "somente_staff": False,
        },
        {
            "id": "financeiro",
            "rotulo": "Financeiro",
            "url": "#",  # TODO: trocar por {% url 'financeiro:home' %} quando o app existir
            "icone": "financeiro",
            "somente_staff": False,
        },
    ]

    itens_visiveis = []
    for item in itens_completos:
        if usuario.is_superuser:
            permitido = True
        elif item["somente_staff"]:
            permitido = usuario.is_staff
        else:
            permitido = item["id"] == setor_usuario_id

        if permitido:
            item["permitido"] = True
            itens_visiveis.append(item)

    return {
        "menu_lateral": itens_visiveis,
        "setor_usuario": setor_usuario_id,
    }