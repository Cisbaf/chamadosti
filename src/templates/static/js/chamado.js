(function () {
  'use strict';

  var $ = function (s, r) { return (r || document).querySelector(s); };
  var $$ = function (s, r) { return Array.prototype.slice.call((r || document).querySelectorAll(s)); };
  var lerJson = function (id) { return JSON.parse(document.getElementById(id).textContent); };

  var LOCAIS = lerJson('dados-localizacoes');
  var SUBMOTIVOS = lerJson('dados-submotivos');
  var CAMPOS_LOGIN = lerJson('dados-campos-login');
  var MAX_ARQUIVOS = 2;
  var MAX_BYTES = 15 * 1024 * 1024;
  var EXT_OK = ['jpg', 'jpeg', 'png', 'gif', 'pdf'];
  var TIMEOUT_ENVIO_MS = 90000;

  var CAMINHOS = {};
  var LOCAIS_NORM = LOCAIS.map(function (l) {
    CAMINHOS[l.id] = l.caminho;
    return { id: l.id, caminho: l.caminho, alvo: normalizar(l.caminho) };
  });

  function normalizar(s) {
    return String(s || '').normalize('NFD').replace(/[̀-ͯ]/g, '').toLowerCase().trim();
  }

  function partes(caminho) {
    var i = caminho.lastIndexOf(' > ');
    if (i === -1) return { pai: 'Município / sede', nome: caminho };
    return { pai: caminho.slice(0, i).split(' > ').join(' › ') + ' ›', nome: caminho.slice(i + 3) };
  }

  function mascara(v) {
    var d = String(v || '').replace(/\D/g, '').slice(0, 11);
    if (d.length <= 2) return d.length ? '(' + d : '';
    if (d.length <= 7) return '(' + d.slice(0, 2) + ') ' + d.slice(2);
    return '(' + d.slice(0, 2) + ') ' + d.slice(2, 7) + '-' + d.slice(7);
  }

  function formatarTamanho(bytes) {
    if (bytes >= 1024 * 1024) return (bytes / 1024 / 1024).toFixed(1).replace('.', ',') + ' MB';
    return (bytes > 0 ? Math.max(1, Math.round(bytes / 1024)) : 0) + ' KB';
  }

  function novoToken() {
    if (window.crypto && crypto.randomUUID) return crypto.randomUUID();
    var a = new Uint8Array(16);
    (window.crypto || window.msCrypto).getRandomValues(a);
    return Array.prototype.map.call(a, function (b) { return ('0' + b.toString(16)).slice(-2); }).join('');
  }

  function csrf() {
    var m = document.cookie.match(/(?:^|; )csrftoken=([^;]+)/);
    return m ? decodeURIComponent(m[1]) : '';
  }

  /* ---------- Seletor de localização (busca com autocompletar) ---------- */
  function criarSeletor(raiz, idInput, aoMudar) {
    raiz.appendChild(document.getElementById('tpl-loc').content.cloneNode(true));
    var elSel = $('.loc-selecionada', raiz);
    var elBusca = $('.loc-busca', raiz);
    var input = $('input', raiz);
    var elRes = $('.loc-resultados', raiz);
    var elCont = $('.loc-contagem', raiz);
    var elLista = $('.loc-lista', raiz);
    var elNenhum = $('.loc-nenhum', raiz);
    var atual = null;
    var automatico = false;
    input.id = idInput;

    function mostrarSelecao() {
      elSel.hidden = atual === null;
      elBusca.hidden = atual !== null;
      if (atual !== null) {
        var p = partes(CAMINHOS[atual]);
        $('.loc-pai', elSel).textContent = p.pai;
        $('.loc-nome', elSel).textContent = p.nome;
      }
    }

    function escolher(id, viaAutomatico) {
      atual = id;
      automatico = !!viaAutomatico;
      input.value = '';
      input.classList.remove('invalido');
      elRes.hidden = true;
      elNenhum.hidden = true;
      mostrarSelecao();
      aoMudar();
    }

    function buscar() {
      var termos = normalizar(input.value).split(/\s+/).filter(Boolean);
      var achados = termos.length ? LOCAIS_NORM.filter(function (l) {
        return termos.every(function (t) { return l.alvo.indexOf(t) !== -1; });
      }) : [];
      elLista.textContent = '';
      achados.forEach(function (l) {
        var p = partes(l.caminho);
        var b = document.createElement('button');
        b.type = 'button';
        var pai = document.createElement('span');
        pai.className = 'loc-pai';
        pai.textContent = p.pai;
        var nome = document.createElement('span');
        nome.className = 'loc-nome';
        nome.textContent = p.nome;
        b.appendChild(pai);
        b.appendChild(nome);
        b.addEventListener('click', function () { escolher(l.id); });
        elLista.appendChild(b);
      });
      elRes.hidden = achados.length === 0;
      elNenhum.hidden = !(termos.length && achados.length === 0);
      elCont.textContent = achados.length === 1 ? '1 local encontrado' : achados.length + ' locais encontrados';
      elLista.scrollTop = 0;
      input.dataset.primeiro = achados.length ? achados[0].id : '';
    }

    input.addEventListener('input', function () { input.classList.remove('invalido'); buscar(); });
    input.addEventListener('keydown', function (e) {
      if (e.key === 'Enter') {
        e.preventDefault();
        if (input.dataset.primeiro) escolher(Number(input.dataset.primeiro));
      }
    });
    $('.btn-trocar', raiz).addEventListener('click', function () {
      atual = null;
      mostrarSelecao();
      aoMudar();
      input.focus();
    });
    mostrarSelecao();

    return {
      get id() { return atual; },
      get automatico() { return automatico && atual !== null; },
      set: function (id) { if (CAMINHOS[id]) escolher(id, true); },
      limpar: function () { atual = null; automatico = false; input.value = ''; elRes.hidden = true; elNenhum.hidden = true; mostrarSelecao(); },
      marcarInvalido: function () { input.classList.add('invalido'); return atual === null ? input : $('.btn-trocar', raiz); }
    };
  }

  /* ---------- Estado e elementos ---------- */
  var st = { passo: 1, arquivos: [], proxArquivo: 1, enviando: false, token: novoToken(), nomeAuto: false, ultimoTel: '', nome3Auto: false, ultimoTel3: '' };

  var elTel = $('#f-tel'), elNome = $('#f-nome');
  var elTerceiro = $('#f-terceiro'), elNome3 = $('#f-nome3'), elTel3 = $('#f-tel3');
  var elMotivo = $('#f-motivo'), elDesc = $('#f-desc');
  var elErro = $('#erro');
  var btnVoltar = $('#btn-voltar'), btnProximo = $('#btn-proximo'), btnEnviar = $('#btn-enviar');
  var elConhecido = $('#conhecido');

  var loc1 = criarSeletor($('#loc1'), 'f-loc1', atualizarParaMim);
  var loc2 = criarSeletor($('#loc2'), 'f-loc2', function () {});

  var subSelecionada = '';
  var camposLogin = {};

  /* ---------- Etapas ---------- */
  var CHECK = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M20 6 9 17l-5-5"></path></svg>';

  function atualizarEtapas() {
    $$('.etapas li').forEach(function (li) {
      var n = Number(li.dataset.etapa);
      li.classList.toggle('feito', n < st.passo);
      li.classList.toggle('atual', n === st.passo);
      var b = $('.bolinha', li);
      if (n < st.passo) { b.innerHTML = CHECK; b.removeAttribute('aria-current'); }
      else { b.textContent = n; if (n === st.passo) b.setAttribute('aria-current', 'step'); else b.removeAttribute('aria-current'); }
    });
  }

  function mostrarPasso(n, moverFoco) {
    st.passo = n;
    $$('.passo').forEach(function (s) { s.hidden = Number(s.dataset.passo) !== n; });
    btnVoltar.hidden = n === 1;
    btnProximo.hidden = n === 4;
    btnEnviar.hidden = n !== 4;
    limparErro();
    atualizarEtapas();
    if (n === 2) atualizarParaMim();
    if (n === 4) { atualizarResumo(); atualizarAnexos(); }
    if (moverFoco) {
      var titulo = $('.passo[data-passo="' + n + '"] h2');
      if (titulo) titulo.focus({ preventScroll: true });
      var cartao = $('#cartao');
      if (cartao.getBoundingClientRect().top < 0) cartao.scrollIntoView({ block: 'start' });
    }
  }

  function limparErro() {
    elErro.hidden = true;
    elErro.textContent = '';
    $$('.invalido').forEach(function (e) { e.classList.remove('invalido'); });
  }

  function mostrarErro(msg, alvo) {
    elErro.textContent = msg;
    elErro.hidden = false;
    if (alvo) {
      alvo.classList.add('invalido');
      if (alvo.focus) alvo.focus({ preventScroll: false });
    }
  }

  /* ---------- Validação (o servidor repete tudo) ---------- */
  var RE_NOME = /^[\p{L}]+(?:[ '’\-]+[\p{L}]+)*$/u;
  var RE_LETRA = /\p{L}/gu;
  var RE_CEL = /^\(\d{2}\) \d{5}-\d{4}$/;
  var RE_EMAIL = /^[^@\s]+@[^@\s]+\.[^@\s]+$/;

  function nomeErro(valor, rotulo) {
    valor = valor.trim().replace(/\s+/g, ' ');
    if (!valor) return 'Preencha ' + rotulo + '.';
    if (/\d/.test(valor)) return 'O nome não pode ter números.';
    if (!RE_NOME.test(valor) || (valor.match(RE_LETRA) || []).length < 3) return 'Preencha ' + rotulo + ', só com letras (mínimo 3).';
    return '';
  }

  function cpfErro(v) {
    if (!v) return 'Preencha o campo CPF.';
    if (!/^\d+$/.test(v)) return 'O CPF deve ter só números, sem pontos nem traço.';
    if (v.length !== 11) return 'O CPF deve ter 11 números.';
    if (/^(\d)\1{10}$/.test(v)) return 'CPF inválido. Confira os números.';
    for (var t = 9; t <= 10; t++) {
      var soma = 0;
      for (var i = 0; i < t; i++) soma += Number(v[i]) * (t + 1 - i);
      if ((soma * 10 % 11) % 10 !== Number(v[t])) return 'CPF inválido. Confira os números.';
    }
    return '';
  }

  function validar(passo) {
    if (passo === 1) {
      if (!RE_CEL.test(elTel.value)) return { msg: 'Informe o celular completo com DDD: (21) 99999-9999.', el: elTel };
      var e = nomeErro(elNome.value, 'o seu nome completo');
      if (e) return { msg: e, el: elNome };
      if (loc1.id === null) return { msg: 'Escolha a sua localização na lista.', el: loc1.marcarInvalido() };
    }
    if (passo === 2 && elTerceiro.checked) {
      if (!RE_CEL.test(elTel3.value)) return { msg: 'Informe o celular da outra pessoa com DDD: (21) 99999-9999.', el: elTel3 };
      var e3 = nomeErro(elNome3.value, 'o nome da outra pessoa');
      if (e3) return { msg: e3, el: elNome3 };
      if (loc2.id === null) return { msg: 'Escolha a localização da outra pessoa na lista.', el: loc2.marcarInvalido() };
    }
    if (passo === 3) {
      var motivo = elMotivo.value;
      if (!motivo) return { msg: 'Selecione o motivo.', el: elMotivo };
      if (SUBMOTIVOS[motivo] && !subSelecionada) return { msg: 'Marque uma opção.', el: $('#subs-lista input') };
      if (motivo === 'Criação de Login') {
        var rotulos = CAMPOS_LOGIN[subSelecionada] || [];
        for (var i = 0; i < rotulos.length; i++) {
          var r = rotulos[i];
          var inp = $('#campos-lista input[data-rotulo="' + r + '"]');
          var v = (inp.value || '').trim();
          if (r === 'Nome Completo') { var en = nomeErro(v, 'o campo Nome Completo'); if (en) return { msg: en, el: inp }; }
          else if (r === 'CPF') { var ec = cpfErro(v); if (ec) return { msg: ec, el: inp }; }
          else if (!v) return { msg: 'Preencha o campo ' + r + '.', el: inp };
          else if (r === 'Email' && !RE_EMAIL.test(v)) return { msg: 'Informe um e-mail válido.', el: inp };
        }
      } else if (elDesc.value.trim().length < 5) {
        return { msg: 'Descreva o problema.', el: elDesc };
      }
    }
    return null;
  }

  /* ---------- Celular e preenchimento automático (solicitante e outra pessoa) ---------- */
  var elConhecido3 = $('#conhecido3');

  function consultarCadastro(digitos, alvo) {
    fetch('/api/solicitante/' + digitos, { credentials: 'same-origin' })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (dados) {
        if (!dados || !dados.encontrado || alvo.tel.value.replace(/\D/g, '') !== digitos) return;
        if (dados.nome && (!alvo.nome.value.trim() || st[alvo.auto])) {
          alvo.nome.value = dados.nome;
          st[alvo.auto] = true;
          alvo.nome.classList.remove('invalido');
        }
        if (dados.localizacao_id && alvo.loc.id === null) alvo.loc.set(dados.localizacao_id);
        alvo.aviso.querySelector('span').textContent = dados.localizacao_id
          ? 'Número cadastrado: preenchemos nome e localização.'
          : 'Número cadastrado: preenchemos o nome. Escolha a localização.';
        alvo.aviso.hidden = false;
      })
      .catch(function () { /* preenchimento é só conveniência */ });
  }

  function ligarCelular(alvo) {
    alvo.tel.addEventListener('input', function () {
      alvo.tel.value = mascara(alvo.tel.value);
      alvo.tel.classList.remove('invalido');
      var d = alvo.tel.value.replace(/\D/g, '');
      if (d !== st[alvo.ultimo] && st[alvo.ultimo]) {
        // o número mudou: o que veio do cadastro do número anterior não vale mais
        if (st[alvo.auto]) { alvo.nome.value = ''; st[alvo.auto] = false; }
        if (alvo.loc.automatico) alvo.loc.limpar();
        alvo.aviso.hidden = true;
        st[alvo.ultimo] = '';
      }
      if (d.length < 11) { alvo.aviso.hidden = true; return; }
      if (d !== st[alvo.ultimo]) { st[alvo.ultimo] = d; consultarCadastro(d, alvo); }
    });
    alvo.nome.addEventListener('input', function () { st[alvo.auto] = false; alvo.nome.classList.remove('invalido'); });
  }

  ligarCelular({ tel: elTel, nome: elNome, loc: loc1, aviso: elConhecido, auto: 'nomeAuto', ultimo: 'ultimoTel' });
  ligarCelular({ tel: elTel3, nome: elNome3, loc: loc2, aviso: elConhecido3, auto: 'nome3Auto', ultimo: 'ultimoTel3' });
  [elMotivo, elDesc].forEach(function (e) { e.addEventListener('input', function () { e.classList.remove('invalido'); }); });

  /* ---------- Passo 2 ---------- */
  function atualizarParaMim() {
    $('#pm-nome').textContent = elNome.value.trim() || '—';
    $('#pm-local').textContent = loc1.id === null ? '—' : CAMINHOS[loc1.id].split(' > ').join(' › ');
  }
  elTerceiro.addEventListener('change', function () {
    $('#outra').hidden = !elTerceiro.checked;
    $('#para-mim').hidden = elTerceiro.checked;
    limparErro();
  });

  /* ---------- Passo 3 ---------- */
  function montarSubmotivos() {
    var motivo = elMotivo.value;
    var itens = SUBMOTIVOS[motivo] || [];
    subSelecionada = '';
    camposLogin = {};
    var lista = $('#subs-lista');
    lista.textContent = '';
    $('#subs').hidden = !itens.length;
    $('#subs-titulo').textContent = motivo === 'Criação de Login' ? 'Para qual sistema?' : 'Qual sistema?';
    itens.forEach(function (rotulo) {
      var label = document.createElement('label');
      var radio = document.createElement('input');
      radio.type = 'radio';
      radio.name = 'sub-motivo';
      radio.addEventListener('change', function () { subSelecionada = rotulo; limparErro(); montarCampos(); });
      var texto = document.createElement('span');
      texto.textContent = rotulo;
      label.appendChild(radio);
      label.appendChild(texto);
      lista.appendChild(label);
    });
    montarCampos();
  }

  function montarCampos() {
    var motivo = elMotivo.value;
    var rotulos = motivo === 'Criação de Login' ? (CAMPOS_LOGIN[subSelecionada] || []) : [];
    var lista = $('#campos-lista');
    lista.textContent = '';
    rotulos.forEach(function (r) {
      var label = document.createElement('label');
      var span = document.createElement('span');
      span.textContent = r;
      var inp = document.createElement('input');
      inp.type = r === 'Email' ? 'email' : 'text';
      inp.maxLength = 200;
      if (r === 'CPF') {
        inp.inputMode = 'numeric';
        inp.maxLength = 11;
        inp.autocomplete = 'off';
        inp.placeholder = 'Somente números';
        inp.addEventListener('input', function () { inp.value = inp.value.replace(/\D/g, '').slice(0, 11); });
      }
      inp.dataset.rotulo = r;
      inp.addEventListener('input', function () { inp.classList.remove('invalido'); });
      label.appendChild(span);
      label.appendChild(inp);
      lista.appendChild(label);
    });
    $('#campos-login').hidden = rotulos.length === 0;
    $('#campo-desc').hidden = motivo === 'Criação de Login';
  }
  elMotivo.addEventListener('change', function () { limparErro(); montarSubmotivos(); });

  /* ---------- Passo 4: anexos e resumo ---------- */
  var ICONE_FOTO = '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="3" y="4" width="18" height="16" rx="2"></rect><circle cx="9" cy="10" r="2"></circle><path d="m21 17-5-5-8 8"></path></svg>';
  var ICONE_LIXO = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><path d="M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3"></path></svg>';

  function totalBytes() { return st.arquivos.reduce(function (s, a) { return s + a.file.size; }, 0); }

  function atualizarAnexos() {
    var lista = $('#anexos-lista');
    lista.textContent = '';
    st.arquivos.forEach(function (a) {
      var linha = document.createElement('div');
      linha.className = 'anexo';
      linha.insertAdjacentHTML('beforeend', ICONE_FOTO);
      var info = document.createElement('div');
      var nome = document.createElement('span');
      nome.className = 'anexo-nome';
      nome.textContent = a.file.name;
      var tam = document.createElement('span');
      tam.className = 'anexo-tam';
      tam.textContent = formatarTamanho(a.file.size);
      info.appendChild(nome);
      info.appendChild(tam);
      var rem = document.createElement('button');
      rem.type = 'button';
      rem.setAttribute('aria-label', 'Remover arquivo ' + a.file.name);
      rem.innerHTML = ICONE_LIXO;
      rem.addEventListener('click', function () {
        st.arquivos = st.arquivos.filter(function (x) { return x.id !== a.id; });
        limparErro();
        atualizarAnexos();
      });
      linha.appendChild(info);
      linha.appendChild(rem);
      lista.appendChild(linha);
    });
    $('#btn-anexo').disabled = st.arquivos.length >= MAX_ARQUIVOS;
    $('#anexos-uso').textContent = st.arquivos.length + '/' + MAX_ARQUIVOS + ' arquivos, ' + formatarTamanho(totalBytes()) +
      ' · até 2 arquivos, somando no máximo 15 MB. Fotos ou PDF.';
  }

  $('#btn-anexo').addEventListener('click', function () { $('#f-arquivo').click(); });
  $('#f-arquivo').addEventListener('change', function (e) {
    var arq = e.target.files && e.target.files[0];
    e.target.value = '';
    if (!arq) return;
    limparErro();
    var ext = (arq.name.split('.').pop() || '').toLowerCase();
    if (EXT_OK.indexOf(ext) === -1) return mostrarErro('Envie só fotos (JPG, PNG, GIF) ou PDF.');
    if (st.arquivos.length >= MAX_ARQUIVOS) return mostrarErro('Envie no máximo ' + MAX_ARQUIVOS + ' arquivos.');
    if (arq.size === 0) return mostrarErro('Esse arquivo está vazio.');
    if (totalBytes() + arq.size > MAX_BYTES) return mostrarErro('Os anexos somam mais de 15 MB. Escolha um arquivo menor.');
    st.arquivos.push({ id: st.proxArquivo++, file: arq });
    atualizarAnexos();
  });

  function atualizarResumo() {
    var terceiro = elTerceiro.checked;
    $('#rs-para').textContent = terceiro ? elNome3.value.trim() + ' (aberto por ' + elNome.value.trim() + ')' : elNome.value.trim();
    var loc = terceiro ? loc2.id : loc1.id;
    $('#rs-local').textContent = loc === null ? '—' : CAMINHOS[loc].split(' > ').join(' › ');
    $('#rs-motivo').textContent = (elMotivo.value || '—') + (subSelecionada ? ' › ' + subSelecionada : '');
  }

  /* ---------- Navegação ---------- */
  btnVoltar.addEventListener('click', function () { mostrarPasso(Math.max(1, st.passo - 1), true); });
  btnProximo.addEventListener('click', function () {
    var erro = validar(st.passo);
    if (erro) return mostrarErro(erro.msg, erro.el);
    mostrarPasso(Math.min(4, st.passo + 1), true);
  });
  $$('input[type="text"], input[type="tel"]').forEach(function (inp) {
    inp.addEventListener('keydown', function (e) { if (e.key === 'Enter') { e.preventDefault(); if (st.passo < 4) btnProximo.click(); } });
  });

  /* ---------- Envio ---------- */
  function dadosDoPedido() {
    var motivo = elMotivo.value;
    var campos = {};
    if (motivo === 'Criação de Login') {
      $$('#campos-lista input').forEach(function (i) { campos[i.dataset.rotulo] = i.value.trim(); });
    }
    var d = {
      token: st.token,
      nome: elNome.value.trim(),
      celular: elTel.value.replace(/\D/g, ''),
      localizacao_id: loc1.id,
      outra_pessoa: elTerceiro.checked,
      motivo: motivo,
      sub_motivo: subSelecionada,
      campos: campos,
      descricao: motivo === 'Criação de Login' ? '' : elDesc.value.trim()
    };
    if (d.outra_pessoa) {
      d.outra_nome = elNome3.value.trim();
      d.outra_celular = elTel3.value.replace(/\D/g, '');
      d.outra_localizacao_id = loc2.id;
    }
    return d;
  }

  function passoDoCampo(chave) {
    if (chave === 'anexos') return 4;
    if (chave.indexOf('outra_') === 0) return 2;
    if (['nome', 'celular', 'localizacao_id'].indexOf(chave) !== -1) return 1;
    return 3;
  }

  function mostrarTela(qual) {
    $('#formulario').hidden = qual !== 'form';
    $('#tela-criado').hidden = qual !== 'criado';
    $('#tela-falhou').hidden = qual !== 'falhou';
    if (qual !== 'form') {
      var t = $('#tela-' + qual + ' h2');
      t.focus({ preventScroll: true });
      $('#cartao').scrollIntoView({ block: 'start' });
    }
  }

  function falhou(texto) {
    $('#falhou-texto').textContent = texto;
    mostrarTela('falhou');
  }

  function setEnviando(sim) {
    st.enviando = sim;
    btnEnviar.disabled = sim;
    $('span', btnEnviar).textContent = sim ? 'Enviando…' : 'Abrir chamado';
  }

  function enviar() {
    if (st.enviando) return;
    for (var p = 1; p <= 3; p++) {
      var erro = validar(p);
      if (erro) { mostrarPasso(p, false); return mostrarErro(erro.msg, erro.el); }
    }
    setEnviando(true);
    limparErro();
    var fd = new FormData();
    fd.append('data', JSON.stringify(dadosDoPedido()));
    st.arquivos.forEach(function (a) { fd.append('files', a.file, a.file.name); });
    var ctl = window.AbortController ? new AbortController() : null;
    var timer = ctl ? setTimeout(function () { ctl.abort(); }, TIMEOUT_ENVIO_MS) : null;

    fetch('/api/chamados', {
      method: 'POST', body: fd, credentials: 'same-origin',
      headers: { 'X-CSRFToken': csrf() }, signal: ctl ? ctl.signal : undefined
    }).then(function (r) {
      return r.json().catch(function () { return null; }).then(function (corpo) { return { status: r.status, corpo: corpo }; });
    }).then(function (res) {
      var c = res.corpo;
      if ((res.status === 201 || res.status === 200) && c && c.ok) {
        $('#numero-chamado').textContent = c.numero;
        $('#criado-tel').textContent = elTel.value;
        $('#criado-anexo').hidden = !c.anexos_falhos;
        return mostrarTela('criado');
      }
      if (res.status === 422 && c && c.erros) {
        var chaves = Object.keys(c.erros);
        var passo = Math.min.apply(null, chaves.map(passoDoCampo));
        mostrarPasso(passo, false);
        return mostrarErro(c.erros[chaves.filter(function (k) { return passoDoCampo(k) === passo; })[0]]);
      }
      if (res.status === 409) return mostrarErro((c && c.mensagem) || 'Seu pedido já está sendo enviado. Aguarde alguns segundos.');
      if (res.status === 403) return falhou('A página ficou aberta por muito tempo. Atualize a página e preencha de novo.');
      if (res.status === 502) return falhou('O que você preencheu continua aqui. Tente de novo em alguns instantes. A TI já foi avisada.');
      return falhou('Algo deu errado do nosso lado. O que você preencheu continua aqui. Tente de novo em alguns instantes.');
    }).catch(function () {
      falhou('Não conseguimos falar com o servidor. Confira a sua internet; o que você preencheu continua aqui.');
    }).then(function () {
      if (timer) clearTimeout(timer);
      setEnviando(false);
    });
  }
  btnEnviar.addEventListener('click', enviar);

  $('#btn-tentar').addEventListener('click', function () { mostrarTela('form'); mostrarPasso(4, true); });

  $('#btn-novo').addEventListener('click', function () {
    [elTel, elNome, elNome3, elTel3, elDesc].forEach(function (e) { e.value = ''; });
    elMotivo.value = '';
    elTerceiro.checked = false;
    $('#outra').hidden = true;
    $('#para-mim').hidden = false;
    elConhecido.hidden = true;
    elConhecido3.hidden = true;
    loc1.limpar();
    loc2.limpar();
    montarSubmotivos();
    st.arquivos = [];
    st.nomeAuto = false;
    st.ultimoTel = '';
    st.nome3Auto = false;
    st.ultimoTel3 = '';
    st.token = novoToken();
    mostrarTela('form');
    mostrarPasso(1, true);
  });

  mostrarPasso(1, false);
  montarSubmotivos();
})();
