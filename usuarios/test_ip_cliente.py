from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from config.test_criptografia import chaves, gerar_chave
from funcionarios.models import Funcionario
from usuarios.middleware import IPClienteMiddleware
from usuarios.models import LogAuditoria

Usuario = get_user_model()

CABECALHO = 'HTTP_TRUE_CLIENT_IP'
IP_PROXY = '10.0.0.1'
IP_CLIENTE = '203.0.113.7'


class IPClienteMiddlewareTests(SimpleTestCase):
    def executar(self, **meta):
        capturado = {}

        def get_response(request):
            capturado['ip'] = request.META.get('REMOTE_ADDR')
            return HttpResponse()

        IPClienteMiddleware(get_response)(RequestFactory().get('/', **meta))
        return capturado['ip']

    @override_settings(IP_CLIENTE_CABECALHO=CABECALHO)
    def test_usa_o_ip_do_cabecalho_confiavel(self):
        ip = self.executar(REMOTE_ADDR=IP_PROXY, **{CABECALHO: IP_CLIENTE})
        self.assertEqual(ip, IP_CLIENTE)

    @override_settings(IP_CLIENTE_CABECALHO=CABECALHO)
    def test_aceita_ipv6(self):
        ip = self.executar(REMOTE_ADDR=IP_PROXY, **{CABECALHO: '2001:db8::1'})
        self.assertEqual(ip, '2001:db8::1')

    @override_settings(IP_CLIENTE_CABECALHO=CABECALHO)
    def test_cabecalho_invalido_mantem_o_remote_addr(self):
        for valor in ('lixo', '999.999.999.999', '1.2.3.4, 5.6.7.8', ''):
            with self.subTest(valor=valor):
                ip = self.executar(REMOTE_ADDR=IP_PROXY, **{CABECALHO: valor})
                self.assertEqual(ip, IP_PROXY)

    @override_settings(IP_CLIENTE_CABECALHO=CABECALHO)
    def test_sem_cabecalho_mantem_o_remote_addr(self):
        self.assertEqual(self.executar(REMOTE_ADDR=IP_PROXY), IP_PROXY)

    @override_settings(IP_CLIENTE_CABECALHO=None)
    def test_configuracao_desligada_ignora_o_cabecalho(self):
        ip = self.executar(REMOTE_ADDR=IP_PROXY, **{CABECALHO: IP_CLIENTE})
        self.assertEqual(ip, IP_PROXY)


@override_settings(BLIND_INDEX_KEY='c' * 40)
class IPNaAuditoriaTests(TestCase):
    def setUp(self):
        self.enterContext(chaves(gerar_chave()))
        funcionario = Funcionario.objects.create(nome='Ana', cpf='123.456.789-09')
        self.usuario = Usuario.objects.create_user(
            email='ana@exemplo.com', password='SenhaTeste123!', funcionario=funcionario
        )

    def login_com_senha_errada(self):
        return self.client.post(
            reverse('account_login'),
            {'login': 'ana@exemplo.com', 'password': 'senha-errada'},
            REMOTE_ADDR=IP_PROXY,
            **{CABECALHO: IP_CLIENTE},
        )

    @override_settings(IP_CLIENTE_CABECALHO=CABECALHO)
    def test_log_de_falha_de_login_grava_o_ip_do_cliente(self):
        self.login_com_senha_errada()
        log = LogAuditoria.objects.filter(tipo_evento='login_falha').latest('data_hora')
        self.assertEqual(log.ip_address, IP_CLIENTE)

    @override_settings(IP_CLIENTE_CABECALHO=None)
    def test_sem_a_configuracao_o_log_grava_o_ip_de_conexao(self):
        self.login_com_senha_errada()
        log = LogAuditoria.objects.filter(tipo_evento='login_falha').latest('data_hora')
        self.assertEqual(log.ip_address, IP_PROXY)