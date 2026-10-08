from django.db import migrations

from config.criptografia import cifrar, decifrar, indice_cego

PREFIXO_TOKEN = "gAAAA"


def somente_digitos(texto):
    return "".join(caractere for caractere in texto if caractere.isdigit())


def cifrar_dados(apps, schema_editor):
    Funcionario = apps.get_model("funcionarios", "Funcionario")

    vistos = {}
    duplicados = set()
    for registro in Funcionario.objects.all().iterator():
        if not registro.cpf or registro.cpf.startswith(PREFIXO_TOKEN):
            continue
        indice = indice_cego(somente_digitos(registro.cpf))
        if indice in vistos:
            duplicados.update({vistos[indice], registro.pk})
        vistos[indice] = registro.pk
    if duplicados:
        raise RuntimeError(
            "CPFs repetidos após normalização nos funcionários de id: "
            + ", ".join(str(pk) for pk in sorted(duplicados))
            + ". Corrija os cadastros e rode a migration de novo."
        )

    for registro in Funcionario.objects.all().iterator():
        campos = {}
        if registro.cpf and not registro.cpf.startswith(PREFIXO_TOKEN):
            campos["cpf_indice"] = indice_cego(somente_digitos(registro.cpf))
            campos["cpf"] = cifrar(registro.cpf)
        if registro.telefone and not registro.telefone.startswith(PREFIXO_TOKEN):
            campos["telefone"] = cifrar(registro.telefone)
        if campos:
            Funcionario.objects.filter(pk=registro.pk).update(**campos)


def decifrar_dados(apps, schema_editor):
    Funcionario = apps.get_model("funcionarios", "Funcionario")
    for registro in Funcionario.objects.all().iterator():
        campos = {}
        if registro.cpf and registro.cpf.startswith(PREFIXO_TOKEN):
            campos["cpf"] = decifrar(registro.cpf)
        if registro.telefone and registro.telefone.startswith(PREFIXO_TOKEN):
            campos["telefone"] = decifrar(registro.telefone)
        if campos:
            Funcionario.objects.filter(pk=registro.pk).update(**campos)


class Migration(migrations.Migration):

    dependencies = [
        ("funcionarios", "0007_funcionario_cpf_indice_alter_funcionario_cpf_and_more"),
    ]

    operations = [
        migrations.RunPython(cifrar_dados, decifrar_dados),
    ]