from django.db import migrations

def criar_versao_consentimento_inicial(apps, schema_editor):
    # Usamos apps.get_model para garantir compatibilidade com o estado da migração
    VersaoTextoConsentimento = apps.get_model('usuarios', 'VersaoTextoConsentimento')
    
    VersaoTextoConsentimento.objects.get_or_create(
        tipo='tratamento_dados',
        versao='1.0',
        defaults={
            'texto_apresentado': 'Concordo que meus dados pessoais sejam tratados pelo ERP Escola Profissionalizante estritamente para fins de autenticação, segurança, auditoria, gestão administrativa e comunicação institucional, em conformidade com a Política de Privacidade e a Lei Geral de Proteção de Dados (LGPD).',
            'ativa': True
        }
    )

class Migration(migrations.Migration):
    dependencies = [
        ('usuarios', '0011_auto_20261018_2335'),
    ]

    operations = [
        migrations.RunPython(criar_versao_consentimento_inicial),
    ]