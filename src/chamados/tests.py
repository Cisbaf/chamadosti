from unittest import mock

from django.test import Client, SimpleTestCase, TestCase, override_settings

from helpers.glpi_client import GlpiClient, GlpiErro, ResultadoAbertura
from users.models import UserRequest

from . import descricao, localizacoes, validacao
from .models import Envio

PNG = b"\x89PNG\r\n\x1a\n" + b"0" * 50
PDF = b"%PDF-1.4\n" + b"0" * 50
CPF_OK = "52998224725"  # CPF de exemplo com dígitos verificadores corretos


def pedido(**extra):
    base = {
        "nome": "Maria Aparecida Souza",
        "celular": "(21) 98765-4321",
        "localizacao_id": 33,
        "motivo": "Suporte Sistemas",
        "sub_motivo": "Suporte SSO",
        "descricao": 'Desde ontem o SSO mostra "senha expirada" e não consigo entrar.',
    }
    base.update(extra)
    return base


class ValidacaoTest(SimpleTestCase):
    def erros(self, **extra):
        limpo, erros = validacao.validar(pedido(**extra))
        return erros

    def test_pedido_valido(self):
        limpo, erros = validacao.validar(pedido())
        self.assertEqual(erros, {})
        self.assertEqual(limpo["celular"], "21987654321")
        self.assertFalse(limpo["outra_pessoa"])

    def test_celular(self):
        for ruim in ["(21) 9876-4321", "2198765432", "219876543210", "(21) 98765-43a1", "", None, 21987654321]:
            self.assertIn("celular", self.erros(celular=ruim), ruim)
        self.assertEqual(self.erros(celular="21987654321"), {})

    def test_nome(self):
        for ruim in ["", "Jo", "João2", "Ana <b>", "123", "--- ---", "A B"]:
            self.assertIn("nome", self.erros(nome=ruim), ruim)
        for bom in ["João", "Ana-Lúcia Ramos", "D'Ávila Souza", "  Maria   Silva "]:
            self.assertEqual(self.erros(nome=bom), {}, bom)

    def test_numero_no_nome_tem_mensagem_propria(self):
        self.assertEqual(self.erros(nome="João2")["nome"], "O nome não pode ter números.")

    def test_localizacao(self):
        for ruim in [None, 0, 99999, "abc", True]:
            self.assertIn("localizacao_id", self.erros(localizacao_id=ruim))
        self.assertEqual(self.erros(localizacao_id="33"), {})

    def test_motivo_e_submotivo(self):
        self.assertIn("motivo", self.erros(motivo="Outro motivo"))
        self.assertIn("sub_motivo", self.erros(sub_motivo=""))
        self.assertIn("sub_motivo", self.erros(sub_motivo="Qualquer"))
        self.assertEqual(self.erros(motivo="Suporte Computador", sub_motivo=""), {})

    def test_descricao_obrigatoria(self):
        self.assertIn("descricao", self.erros(descricao=""))
        self.assertIn("descricao", self.erros(descricao="abc"))
        self.assertIn("descricao", self.erros(descricao="x" * 5001))

    def test_outra_pessoa_exige_tres_campos(self):
        erros = self.erros(outra_pessoa=True)
        self.assertEqual(set(erros), {"outra_nome", "outra_celular", "outra_localizacao_id"})
        ok = self.erros(outra_pessoa=True, outra_nome="Ana Lúcia", outra_celular="21977771020", outra_localizacao_id=59)
        self.assertEqual(ok, {})

    def test_campos_da_outra_pessoa_sao_ignorados_se_nao_marcada(self):
        limpo, erros = validacao.validar(pedido(outra_nome="123"))
        self.assertEqual(erros, {})
        self.assertEqual(limpo["outra_nome"], "")

    def test_criacao_de_login(self):
        base = dict(motivo="Criação de Login", sub_motivo="Sistemas SSO", descricao="")
        erros = self.erros(**base)
        self.assertEqual(set(erros), {"campos.Nome Completo", "campos.CPF", "campos.Cargo"})
        ok = self.erros(**base, campos={"Nome Completo": "Carlos Souza", "CPF": CPF_OK, "Cargo": "Médico"})
        self.assertEqual(ok, {})
        mf = dict(base, sub_motivo="Sistema Marque Fácil")
        erros = self.erros(**mf, campos={"Nome Completo": "Carlos Souza", "CPF": CPF_OK, "Cargo": "x", "Email": "ruim", "Município": "Caxias"})
        self.assertEqual(set(erros), {"campos.Email"})
        erros = self.erros(**base, campos={"Nome Completo": "Carlos 2", "CPF": CPF_OK, "Cargo": "x"})
        self.assertEqual(set(erros), {"campos.Nome Completo"})

    def test_cpf_so_numeros_com_digitos_validos(self):
        base = dict(motivo="Criação de Login", sub_motivo="Sistemas SSO", descricao="")
        def com(cpf):
            return self.erros(**base, campos={"Nome Completo": "Carlos Souza", "CPF": cpf, "Cargo": "Médico"})
        self.assertEqual(com(CPF_OK), {})
        casos = {
            "529.982.247-25": "só números",       # formatado
            "529 982 247 25": "só números",       # espaços
            "5299822472a": "só números",
            "5299822472": "11 números",           # curto
            "529982247251": "11 números",         # longo
            "11111111111": "inválido",            # repetido
            "52998224724": "inválido",            # dígito verificador errado
            "": "Preencha",
            "٥٢٩٩٨٢٢٤٧٢٥": "só números",           # dígitos não ASCII
        }
        for cpf, trecho in casos.items():
            erro = com(cpf).get("campos.CPF", "")
            self.assertIn(trecho, erro, cpf)

    def test_token(self):
        self.assertIn("token", self.erros(token="x"))
        self.assertEqual(self.erros(token="abcdef12-3456"), {})

    def test_pedido_que_nao_e_dict(self):
        self.assertEqual(validacao.validar([1])[1], {"geral": "Pedido inválido."})


class AnexosTest(SimpleTestCase):
    def test_validos(self):
        anexos, erro = validacao.validar_anexos([("../../foto 1.PNG", PNG), ("foto 1.pdf", PDF)])
        self.assertEqual(erro, "")
        self.assertEqual([a.nome for a in anexos], ["foto 1.png", "foto 1.pdf"])
        self.assertEqual(anexos[0].content_type, "image/png")

    def test_nomes_repetidos_ficam_unicos(self):
        anexos, _ = validacao.validar_anexos([("a.png", PNG), ("a.png", PNG)])
        self.assertEqual([a.nome for a in anexos], ["a.png", "a-2.png"])

    def test_limites_e_tipo(self):
        self.assertTrue(validacao.validar_anexos([("a.png", PNG)] * 3)[1])
        grande = PNG + b"0" * validacao.MAX_BYTES_ANEXOS
        self.assertTrue(validacao.validar_anexos([("a.png", grande)])[1])
        self.assertTrue(validacao.validar_anexos([("a.png", PNG), ("b.png", PNG + b"0" * validacao.MAX_BYTES_ANEXOS)])[1])
        self.assertTrue(validacao.validar_anexos([("a.exe", b"MZ" + b"0" * 20)])[1])
        self.assertTrue(validacao.validar_anexos([("a.png", b"")])[1])  # vazio

    def test_exatamente_15mb_passa(self):
        conteudo = PNG + b"0" * (validacao.MAX_BYTES_ANEXOS - len(PNG))
        self.assertEqual(validacao.validar_anexos([("a.png", conteudo)])[1], "")


class LocalizacoesTest(SimpleTestCase):
    def test_lista(self):
        self.assertEqual(len(localizacoes.LOCALIZACOES), 117)
        self.assertEqual(localizacoes.caminho(33), "CAXIAS > UPA SARAPUI")

    def test_formato_antigo(self):
        self.assertEqual(localizacoes.id_do_caminho_antigo("CAXIAS-UPA SARAPUI"), 33)
        self.assertEqual(localizacoes.id_do_caminho_antigo("caxias"), 11)
        self.assertIsNone(localizacoes.id_do_caminho_antigo("CISBAF-Qualquer"))
        self.assertIsNone(localizacoes.id_do_caminho_antigo(""))


class DescricaoTest(SimpleTestCase):
    def test_para_mim(self):
        dados, _ = validacao.validar(pedido())
        t = descricao.montar_ticket(dados)
        self.assertEqual(t["name"], "Suporte Sistemas - Maria Aparecida Souza")
        self.assertEqual(t["locations_id"], 33)
        self.assertEqual((t["type"], t["itilcategories_id"], t["status"], t["entities_id"]), (1, 1, 1, 0))
        for trecho in ["Solicitante: Maria Aparecida Souza", "Celular: (21) 98765-4321",
                       "Localização: CAXIAS &gt; UPA SARAPUI", "Motivo: Suporte Sistemas › Suporte SSO",
                       "&quot;senha expirada&quot;"]:
            self.assertIn(trecho, t["content"])

    def test_outra_pessoa_usa_localizacao_dela(self):
        dados, erros = validacao.validar(pedido(
            outra_pessoa=True, outra_nome="Ana Lúcia Ramos", outra_celular="21977771020", outra_localizacao_id=59,
            motivo="Suporte Computador", sub_motivo=""))
        self.assertEqual(erros, {})
        t = descricao.montar_ticket(dados)
        self.assertEqual(t["name"], "Suporte Computador - Ana Lúcia Ramos")  # provisório
        self.assertEqual(t["locations_id"], 59)
        self.assertIn("Terceiro: Ana Lúcia Ramos", t["content"])
        self.assertIn("Solicitante: Maria Aparecida Souza", t["content"])
        self.assertNotIn("Atendido", t["content"])
        self.assertNotIn("Aberto por", t["content"])
        self.assertLess(t["content"].index("Solicitante:"), t["content"].index("Terceiro:"))

    def test_titulo_final_leva_o_numero(self):
        dados, _ = validacao.validar(pedido(motivo="Suporte Tablet", sub_motivo=""))
        self.assertEqual(descricao.titulo_final(dados, 4143), "Suporte Tablet - #4143")

    def test_html_do_usuario_e_escapado(self):
        dados, _ = validacao.validar(pedido(descricao="<script>alert(1)</script> linha\nsegunda"))
        c = descricao.montar_ticket(dados)["content"]
        self.assertNotIn("<script>", c)
        self.assertIn("&lt;script&gt;", c)
        self.assertIn("<br>segunda", c)

    def test_criacao_de_login(self):
        dados, erros = validacao.validar(pedido(
            motivo="Criação de Login", sub_motivo="Sistemas SSO", descricao="",
            campos={"Nome Completo": "Carlos Souza", "CPF": CPF_OK, "Cargo": "Médico"}))
        self.assertEqual(erros, {})
        c = descricao.montar_ticket(dados)["content"]
        self.assertIn("Nome Completo: Carlos Souza | CPF: 52998224725 | Cargo: Médico", c)
        self.assertNotIn("Descrição:", c)


@override_settings(WHATSAPP_SINCRONO=True, CONTACT_NOTIFICATION="grupo@g.us")
class ApiTest(TestCase):
    def setUp(self):
        self.client = Client(enforce_csrf_checks=False)
        self.glpi = mock.MagicMock()
        self.glpi.__enter__.return_value = self.glpi
        self.glpi.abrir_chamado.return_value = ResultadoAbertura(ticket_id=1234)
        p1 = mock.patch("chamados.views.GlpiClient.das_configuracoes", return_value=self.glpi)
        self.disparar = mock.patch("chamados.views.whatsapp.disparar").start()
        p1.start()
        self.addCleanup(mock.patch.stopall)

    def post(self, dados, arquivos=(), **kw):
        import json
        from django.core.files.uploadedfile import SimpleUploadedFile
        corpo = {"data": json.dumps(dados)}
        if arquivos:
            corpo["files"] = [SimpleUploadedFile(n, c) for n, c in arquivos]
        return self.client.post("/api/chamados", corpo, **kw)

    def test_sucesso(self):
        r = self.post(pedido(), [("tela.png", PNG)])
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json(), {"ok": True, "numero": 1234, "anexos_falhos": 0})
        entrada, anexos, titulo = self.glpi.abrir_chamado.call_args.args
        self.assertEqual(entrada["locations_id"], 33)
        self.assertEqual(anexos[0].nome, "tela.png")
        self.assertEqual(titulo(1234), "Suporte Sistemas - #1234")
        mensagens = self.disparar.call_args.args[0]
        self.assertEqual([m[2] for m in mensagens], [False, True])
        self.assertEqual(mensagens[0][0], "21987654321")
        self.assertIn("nº 1234", mensagens[0][1])
        self.assertEqual(mensagens[1][0], "grupo@g.us")
        c = UserRequest.objects.get(number_applicant="21987654321")
        self.assertEqual((c.name_applicant, c.location_id), ("Maria Aparecida Souza", 33))

    def test_outra_pessoa_avisa_as_duas_e_a_ti(self):
        r = self.post(pedido(outra_pessoa=True, outra_nome="Ana Lúcia", outra_celular="21977771020", outra_localizacao_id=59))
        self.assertEqual(r.status_code, 201)
        mensagens = self.disparar.call_args.args[0]
        self.assertEqual([m[0] for m in mensagens], ["21987654321", "21977771020", "grupo@g.us"])
        self.assertIn("a pedido de Maria Aparecida Souza", mensagens[1][1])
        # o cadastro guarda quem abriu e também a outra pessoa (para preencher sozinho da próxima vez)
        self.assertEqual(UserRequest.objects.count(), 2)
        ana = UserRequest.objects.get(number_applicant="21977771020")
        self.assertEqual((ana.name_applicant, ana.location_id), ("Ana Lúcia", 59))

    def test_invalido_nao_chama_glpi_nem_whatsapp(self):
        r = self.post(pedido(celular="123", nome="X1"))
        self.assertEqual(r.status_code, 422)
        self.assertEqual(set(r.json()["erros"]), {"celular", "nome"})
        self.glpi.abrir_chamado.assert_not_called()
        self.disparar.assert_not_called()

    def test_anexo_invalido(self):
        r = self.post(pedido(), [("a.exe", b"MZ0000")])
        self.assertEqual(r.status_code, 422)
        self.assertIn("anexos", r.json()["erros"])
        self.glpi.abrir_chamado.assert_not_called()

    def test_json_quebrado(self):
        r = self.client.post("/api/chamados", {"data": "{nao e json"})
        self.assertEqual(r.status_code, 400)

    def test_json_direto_sem_anexos(self):
        r = self.client.post("/api/chamados", pedido(), content_type="application/json")
        self.assertEqual(r.status_code, 201)

    def test_glpi_fora_do_ar(self):
        self.glpi.__enter__.side_effect = GlpiErro("Não foi possível conectar ao GLPI", tipo="conexao")
        r = self.post(pedido())
        self.assertEqual(r.status_code, 502)
        self.assertEqual(r.json()["erro"], "glpi")
        mensagens = self.disparar.call_args.args[0]
        self.assertEqual(len(mensagens), 1)
        self.assertEqual(mensagens[0][0], "grupo@g.us")
        self.assertIn("FALHA AO ABRIR CHAMADO", mensagens[0][1])
        self.assertIn("conexao", mensagens[0][1])
        self.assertFalse(UserRequest.objects.exists())

    def test_erro_inesperado_tambem_vira_502(self):
        self.glpi.abrir_chamado.side_effect = RuntimeError("boom")
        self.assertEqual(self.post(pedido()).status_code, 502)

    def test_anexo_que_falhou_avisa_a_ti_mas_abre_o_chamado(self):
        self.glpi.abrir_chamado.return_value = ResultadoAbertura(ticket_id=77, anexos_falhos=["tela.png"])
        r = self.post(pedido(), [("tela.png", PNG)])
        self.assertEqual(r.status_code, 201)
        self.assertEqual(r.json()["anexos_falhos"], 1)
        mensagens = self.disparar.call_args.args[0]
        self.assertIn("tela.png", mensagens[-1][1])

    def test_duplo_clique_nao_abre_dois(self):
        dados = pedido(token="abcdef12-0001")
        r1 = self.post(dados)
        r2 = self.post(dados)
        self.assertEqual(r1.status_code, 201)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r2.json()["numero"], 1234)
        self.assertTrue(r2.json()["repetido"])
        self.assertEqual(self.glpi.abrir_chamado.call_count, 1)
        self.assertEqual(self.disparar.call_count, 1)

    def test_envio_em_andamento_devolve_409(self):
        Envio.objects.create(token="abcdef12-0002")
        r = self.post(pedido(token="abcdef12-0002"))
        self.assertEqual(r.status_code, 409)
        self.glpi.abrir_chamado.assert_not_called()

    def test_apos_falha_pode_tentar_de_novo_com_o_mesmo_token(self):
        self.glpi.abrir_chamado.side_effect = [GlpiErro("x", tipo="timeout"), ResultadoAbertura(ticket_id=5)]
        dados = pedido(token="abcdef12-0003")
        self.assertEqual(self.post(dados).status_code, 502)
        r = self.post(dados)
        self.assertEqual((r.status_code, r.json()["numero"]), (201, 5))

    def test_csrf_e_exigido(self):
        c = Client(enforce_csrf_checks=True)
        r = c.post("/api/chamados", {"data": "{}"})
        self.assertEqual(r.status_code, 403)

    def test_so_aceita_post(self):
        self.assertEqual(self.client.get("/api/chamados").status_code, 405)


class SolicitanteTest(TestCase):
    def test_encontra_e_atualiza(self):
        UserRequest.objects.create(name_applicant="Maria", number_applicant="21987654321",
                                   location_applicant="CAXIAS > UPA SARAPUI", location_id=33)
        r = self.client.get("/api/solicitante/(21) 98765-4321")
        self.assertEqual(r.json(), {"encontrado": True, "nome": "Maria", "localizacao_id": 33,
                                    "localizacao": "CAXIAS > UPA SARAPUI"})

    def test_cadastro_antigo_converte_localizacao(self):
        UserRequest.objects.create(name_applicant="Joana", number_applicant="21911112222",
                                   location_applicant="CAXIAS-UPA SARAPUI")
        r = self.client.get("/api/solicitante/21911112222").json()
        self.assertEqual((r["nome"], r["localizacao_id"]), ("Joana", 33))

    def test_cadastro_antigo_sem_correspondencia(self):
        UserRequest.objects.create(name_applicant="Joana", number_applicant="21911112222",
                                   location_applicant="CISBAF-Outro")
        r = self.client.get("/api/solicitante/21911112222").json()
        self.assertEqual((r["nome"], r["localizacao_id"], r["localizacao"]), ("Joana", None, None))

    def test_nao_encontrado_e_invalido(self):
        self.assertEqual(self.client.get("/api/solicitante/21900000000").json(), {"encontrado": False})
        self.assertEqual(self.client.get("/api/solicitante/123").status_code, 400)


class ClienteGlpiTest(SimpleTestCase):
    def cliente(self):
        return GlpiClient("http://glpi/apirest.php/", "app", "usr", timeout=5, requesttype_id=None)

    def resposta(self, status, corpo):
        r = mock.Mock(status_code=status, text=str(corpo))
        r.json.return_value = corpo
        return r

    def test_fluxo_completo_e_headers(self):
        c = self.cliente()
        respostas = [self.resposta(200, {"session_token": "S"}), self.resposta(200, {"session": {"glpiID": 149}}),
                     self.resposta(201, {"id": 9}),
                     self.resposta(200, [{"9": True}]), self.resposta(201, {"id": 3}), self.resposta(200, {})]
        with mock.patch.object(c._http, "request", side_effect=respostas) as req:
            with c as glpi:
                resultado = glpi.abrir_chamado({"name": "x"}, [validacao.Anexo("a.png", PNG, "image/png")],
                                               lambda n: f"Motivo - #{n}")
        self.assertEqual((resultado.ticket_id, resultado.anexos_falhos, resultado.titulo_provisorio), (9, [], False))
        chamadas = req.call_args_list
        self.assertEqual(chamadas[1].args[1], "http://glpi/apirest.php/getFullSession")
        self.assertEqual(chamadas[2].kwargs["json"], {"input": {"name": "x", "_users_id_requester": 149}})
        self.assertEqual(chamadas[3].args[:2], ("PUT", "http://glpi/apirest.php/Ticket/9"))
        self.assertEqual(chamadas[3].kwargs["json"], {"input": {"name": "Motivo - #9"}})
        self.assertEqual(chamadas[4].args[1], "http://glpi/apirest.php/Document")
        chamadas = chamadas[:1] + chamadas[2:3] + chamadas[4:]  # índices abaixo: init, Ticket, Document, kill
        self.assertEqual(chamadas[0].kwargs["headers"]["Authorization"], "user_token usr")
        self.assertEqual(chamadas[0].kwargs["headers"]["App-Token"], "app")
        self.assertEqual(chamadas[1].kwargs["headers"]["Session-Token"], "S")
        self.assertEqual(chamadas[1].args[1], "http://glpi/apirest.php/Ticket")
        self.assertEqual(chamadas[1].kwargs["headers"]["Session-Token"], "S")
        self.assertEqual(chamadas[3].args[1], "http://glpi/apirest.php/killSession")

    def test_falha_ao_renomear_nao_derruba_o_chamado(self):
        c = self.cliente()
        respostas = [self.resposta(200, {"session_token": "S"}), self.resposta(200, {"session": {"glpiID": 149}}),
                     self.resposta(201, {"id": 9}),
                     self.resposta(400, ["ERROR_RIGHT_MISSING", "sem direito"]),
                     self.resposta(201, {"id": 3}), self.resposta(200, {})]
        with mock.patch.object(c._http, "request", side_effect=respostas):
            with c as glpi:
                resultado = glpi.abrir_chamado({"name": "x"}, [validacao.Anexo("a.png", PNG, "image/png")],
                                               lambda n: f"Motivo - #{n}")
        self.assertEqual((resultado.ticket_id, resultado.anexos_falhos, resultado.titulo_provisorio), (9, [], True))

    def test_anexo_que_falha_nao_derruba_o_chamado(self):
        c = self.cliente()
        respostas = [self.resposta(200, {"session_token": "S"}), self.resposta(200, {"session": {"glpiID": 149}}),
                     self.resposta(201, {"id": 9}),
                     self.resposta(400, ["ERROR_UPLOAD", "ruim"]), self.resposta(200, {})]
        with mock.patch.object(c._http, "request", side_effect=respostas):
            with c as glpi:
                resultado = glpi.abrir_chamado({"name": "x"}, [validacao.Anexo("a.png", PNG, "image/png")])
        self.assertEqual((resultado.ticket_id, resultado.anexos_falhos), (9, ["a.png"]))

    def test_origem_so_vai_se_configurada(self):
        c = GlpiClient("http://glpi", "app", "usr", requesttype_id=9)
        c._sessao = "S"
        c._usuario_consultado = True  # sem usuário de serviço conhecido: não envia requerente
        with mock.patch.object(c._http, "request", return_value=self.resposta(201, {"id": 1})) as req:
            c.criar_ticket({"name": "x"})
        self.assertEqual(req.call_args.kwargs["json"], {"input": {"name": "x", "requesttypes_id": 9}})

    def test_se_nao_descobrir_o_usuario_abre_o_chamado_sem_requerente(self):
        c = self.cliente()
        c._sessao = "S"
        respostas = [self.resposta(400, ["ERROR_X", "falhou"]), self.resposta(201, {"id": 1})]
        with mock.patch.object(c._http, "request", side_effect=respostas) as req:
            self.assertEqual(c.criar_ticket({"name": "x"}), 1)
        self.assertEqual(req.call_args.kwargs["json"], {"input": {"name": "x"}})

    def test_erros(self):
        import requests
        c = self.cliente()
        casos = [
            (requests.ConnectionError(), "conexao"),
            (requests.Timeout(), "timeout"),
            (self.resposta(401, ["ERROR_GLPI_LOGIN_USER_TOKEN", "token ruim"]), "auth"),
            (self.resposta(400, ["ERROR_WRONG_APP_TOKEN_PARAMETER", "x"]), "auth"),
            (self.resposta(400, ["ERROR_GLPI_ADD", "x"]), "api"),
        ]
        for efeito, tipo in casos:
            with mock.patch.object(c._http, "request", side_effect=[efeito]):
                with self.assertRaises(GlpiErro) as ctx:
                    c.abrir_sessao()
            self.assertEqual(ctx.exception.tipo, tipo)
            self.assertNotIn("usr", str(ctx.exception).replace("user_token", ""))

    def test_sem_configuracao(self):
        with self.assertRaises(GlpiErro) as ctx:
            GlpiClient("", "", "")
        self.assertEqual(ctx.exception.tipo, "config")
