from django.db import migrations

from config.criptografia import cifrar, decifrar

PREFIXO_TOKEN = "gAAAA"


def cifrar_chaves(apps, schema_editor):
    Configuracao2FA = apps.get_model("usuarios", "Configuracao2FA")
    for registro in Configuracao2FA.objects.all().iterator():
        valor = registro.chave_secreta
        if not valor or valor.startswith(PREFIXO_TOKEN):
            continue
        Configuracao2FA.objects.filter(pk=registro.pk).update(
            chave_secreta=cifrar(valor)
        )


def decifrar_chaves(apps, schema_editor):
    Configuracao2FA = apps.get_model("usuarios", "Configuracao2FA")
    for registro in Configuracao2FA.objects.all().iterator():
        valor = registro.chave_secreta
        if not valor or not valor.startswith(PREFIXO_TOKEN):
            continue
        Configuracao2FA.objects.filter(pk=registro.pk).update(
            chave_secreta=decifrar(valor)
        )


class Migration(migrations.Migration):

    dependencies = [
        ("usuarios", "0006_alter_configuracao2fa_chave_secreta"),
    ]

    operations = [
        migrations.RunPython(cifrar_chaves, decifrar_chaves),
    ]