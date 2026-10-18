from functools import wraps

from django.core.exceptions import PermissionDenied

from .context_processors import _normalizar


def setor_do_usuario(usuario):
    funcionario = getattr(usuario, 'funcionario', None)
    cargo = funcionario.cargo if funcionario else None
    if cargo and cargo.setor:
        return _normalizar(cargo.setor.nome)
    return None


def pode_acessar_setor(usuario, setor):
    if usuario.is_superuser:
        return True
    return setor_do_usuario(usuario) == setor


def setor_requerido(setor):
    def decorador(view):
        @wraps(view)
        def view_protegida(request, *args, **kwargs):
            if not pode_acessar_setor(request.user, setor):
                raise PermissionDenied
            return view(request, *args, **kwargs)
        return view_protegida
    return decorador