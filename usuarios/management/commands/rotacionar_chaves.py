from django.core.management.base import BaseCommand
from django.conf import settings
from django.db import transaction

from config.criptografia import cifrar, decifrar, indice_cego, _obter_fernet
from funcionarios.models import Funcionario, somente_digitos
from usuarios.models_2fa import Configuracao2FA


class Command(BaseCommand):
    help = (
        "Recifra CPF, telefone e chave TOTP com a chave mais nova e "
        "recalcula o cpf_indice. Rode sempre que adicionar uma chave nova "
        "ao FIELD_ENCRYPTION_KEYS."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simula a rotacao sem gravar alteracoes no banco de dados.",
        )

    def handle(self, *args, **options):
        chaves = getattr(settings, "FIELD_ENCRYPTION_KEYS", [])
        chaves = [c.strip() for c in chaves if c and c.strip()]

        if len(chaves) < 2:
            self.stdout.write(
                self.style.WARNING(
                    "Precisa de pelo menos 2 chaves em FIELD_ENCRYPTION_KEYS "
                    "para rotacionar (nova + antiga)."
                )
            )
            return

        dry_run = options.get("dry_run", False)

        # Limpa o cache para pegar a nova lista de chaves do settings
        _obter_fernet.cache_clear()

        rotacionados = 0

        with transaction.atomic():
            # --- Funcionarios: CPF, telefone e cpf_indice ---
            for f in Funcionario.objects.all().iterator():
                campos = {}
                try:
                    if f.cpf:
                        cru = decifrar(f.cpf)
                        campos["cpf"] = cifrar(cru)
                        campos["cpf_indice"] = indice_cego(somente_digitos(cru))
                except Exception:
                    self.stdout.write(
                        self.style.WARNING(f"CPF do funcionario {f.pk} nao pode ser recifrado.")
                    )

                try:
                    if f.telefone:
                        campos["telefone"] = cifrar(decifrar(f.telefone))
                except Exception:
                    self.stdout.write(
                        self.style.WARNING(f"Telefone do funcionario {f.pk} nao pode ser recifrado.")
                    )

                if campos and not dry_run:
                    Funcionario.objects.filter(pk=f.pk).update(**campos)
                if campos:
                    rotacionados += 1

            # --- Usuarios: chave secreta TOTP ---
            for c in Configuracao2FA.objects.all().iterator():
                try:
                    if c.chave_secreta:
                        if not dry_run:
                            Configuracao2FA.objects.filter(pk=c.pk).update(
                                chave_secreta=cifrar(decifrar(c.chave_secreta))
                            )
                        rotacionados += 1
                except Exception:
                    self.stdout.write(
                        self.style.WARNING(f"Chave TOTP do usuario {c.pk} nao pode ser recifrada.")
                    )

        if dry_run:
            self.stdout.write(
                self.style.WARNING(
                    f"[DRY RUN] {rotacionados} registros seriam rotacionados."
                )
            )
        else:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Rotacionados {rotacionados} registros com a chave mais nova."
                )
            )
