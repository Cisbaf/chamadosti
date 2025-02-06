!function(t,e){"object"==typeof exports&&"undefined"!=typeof module?module.exports=e():"function"==typeof define&&define.amd?define(e):(t=t||self).Stepper=e()}(this,function(){"use strict";function t(){return(t=Object.assign||function(t){for(var e=1;e<arguments.length;e++){var n=arguments[e];for(var s in n)Object.prototype.hasOwnProperty.call(n,s)&&(t[s]=n[s])}return t}).apply(this,arguments)}var e=window.Element.prototype.matches,n=function(t,e){return t.closest(e)},s=function(t,e){return new window.Event(t,e)},i=function(t,e){return new window.CustomEvent(t,e)};!function(){if(window.Element.prototype.matches||(e=window.Element.prototype.msMatchesSelector||window.Element.prototype.webkitMatchesSelector),window.Element.prototype.closest||(n=function(t,n){if(!document.documentElement.contains(t))return null;do{if(e.call(t,n))return t;t=t.parentElement||t.parentNode}while(null!==t&&1===t.nodeType);return null}),window.Event&&"function"==typeof window.Event||(s=function(t,e){e=e||{};var n=document.createEvent("Event");return n.initEvent(t,Boolean(e.bubbles),Boolean(e.cancelable)),n}),"function"!=typeof window.CustomEvent){var t=window.Event.prototype.preventDefault;i=function(e,n){var s=document.createEvent("CustomEvent");return n=n||{bubbles:!1,cancelable:!1,detail:null},s.initCustomEvent(e,n.bubbles,n.cancelable,n.detail),s.preventDefault=function(){this.cancelable&&(t.call(this),Object.defineProperty(this,"defaultPrevented",{get:function(){return!0}}))},s}}}();var r={ACTIVE:"active",LINEAR:"linear",BLOCK:"dstepper-block",NONE:"dstepper-none",FADE:"fade",VERTICAL:"vertical"},o="transitionend",c="bsStepper",a=function(t,e,n,s){var o=t[c];if(!o._steps[e].classList.contains(r.ACTIVE)&&!o._stepsContents[e].classList.contains(r.ACTIVE)){var a=i("show.bs-stepper",{cancelable:!0,detail:{from:o._currentIndex,to:e,indexStep:e}});t.dispatchEvent(a);var p=o._steps.filter(function(t){return t.classList.contains(r.ACTIVE)}),d=o._stepsContents.filter(function(t){return t.classList.contains(r.ACTIVE)});a.defaultPrevented||(p.length&&p[0].classList.remove(r.ACTIVE),d.length&&(d[0].classList.remove(r.ACTIVE),t.classList.contains(r.VERTICAL)||o.options.animation||d[0].classList.remove(r.BLOCK)),l(t,o._steps[e],o._steps,n),u(t,o._stepsContents[e],o._stepsContents,d,s))}},l=function(t,e,n,s){n.forEach(function(e){var n=e.querySelector(s.selectors.trigger);n.setAttribute("aria-selected","false"),t.classList.contains(r.LINEAR)&&n.setAttribute("disabled","disabled")}),e.classList.add(r.ACTIVE);var i=e.querySelector(s.selectors.trigger);i.setAttribute("aria-selected","true"),t.classList.contains(r.LINEAR)&&i.removeAttribute("disabled")},u=function(t,e,n,s,a){var l=t[c],u=n.indexOf(e),f=i("shown.bs-stepper",{cancelable:!0,detail:{from:l._currentIndex,to:u,indexStep:u}});if(e.classList.contains(r.FADE)){e.classList.remove(r.NONE);var h=p(e);e.addEventListener(o,function n(){e.classList.add(r.BLOCK),e.removeEventListener(o,n),t.dispatchEvent(f),a()}),s.length&&s[0].classList.add(r.NONE),e.classList.add(r.ACTIVE),d(e,h)}else e.classList.add(r.ACTIVE),e.classList.add(r.BLOCK),t.dispatchEvent(f),a()},p=function(t){if(!t)return 0;var e=window.getComputedStyle(t).transitionDuration;return parseFloat(e)?(e=e.split(",")[0],1e3*parseFloat(e)):0},d=function(t,e){var n=!1,i=e+5;function r(){n=!0,t.removeEventListener(o,r)}t.addEventListener(o,r),window.setTimeout(function(){n||t.dispatchEvent(s(o)),t.removeEventListener(o,r)},i)},f=function(t,e){e.animation&&t.forEach(function(t){t.classList.add(r.FADE),t.classList.add(r.NONE)})},h={linear:!0,animation:!1,selectors:{steps:".step",trigger:".step-trigger",stepper:".bs-stepper"}};return function(){function e(e,n){var s=this;void 0===n&&(n={}),this._element=e,this._currentIndex=0,this._stepsContents=[],this.options=t({},h,{},n),this.options.selectors=t({},h.selectors,{},this.options.selectors),this.options.linear&&this._element.classList.add(r.LINEAR),this._steps=[].slice.call(this._element.querySelectorAll(this.options.selectors.steps)),this._steps.filter(function(t){return t.hasAttribute("data-target")}).forEach(function(t){s._stepsContents.push(s._element.querySelector(t.getAttribute("data-target")))}),f(this._stepsContents,this.options),this._setLinkListeners(),Object.defineProperty(this._element,c,{value:this,writable:!0}),this._steps.length&&a(this._element,this._currentIndex,this.options,function(){})}var s=e.prototype;return s._setLinkListeners=function(){var t=this;this._steps.forEach(function(e){var s,i=e.querySelector(t.options.selectors.trigger);t.options.linear?(t._clickStepLinearListener=(t.options,function(t){t.preventDefault()}),i.addEventListener("click",t._clickStepLinearListener)):(t._clickStepNonLinearListener=(s=t.options,function(t){t.preventDefault();var e=n(t.target,s.selectors.steps),i=n(e,s.selectors.stepper),r=i[c],o=r._steps.indexOf(e);a(i,o,s,function(){r._currentIndex=o})}),i.addEventListener("click",t._clickStepNonLinearListener))})},s.next=function(){var t=this,e=this._currentIndex+1<=this._steps.length-1?this._currentIndex+1:this._steps.length-1;a(this._element,e,this.options,function(){t._currentIndex=e})},s.previous=function(){var t=this,e=this._currentIndex-1>=0?this._currentIndex-1:0;a(this._element,e,this.options,function(){t._currentIndex=e})},s.to=function(t){var e=this,n=t-1,s=n>=0&&n<this._steps.length?n:0;a(this._element,s,this.options,function(){e._currentIndex=s})},s.reset=function(){var t=this;a(this._element,0,this.options,function(){t._currentIndex=0})},s.destroy=function(){var t=this;this._steps.forEach(function(e){var n=e.querySelector(t.options.selectors.trigger);t.options.linear?n.removeEventListener("click",t._clickStepLinearListener):n.removeEventListener("click",t._clickStepNonLinearListener)}),this._element[c]=void 0,this._element=void 0,this._currentIndex=void 0,this._steps=void 0,this._stepsContents=void 0,this._clickStepLinearListener=void 0,this._clickStepNonLinearListener=void 0},e}()});

var StepperComponent;

var elements = {
    containerInputs: null,
    containerBases: null,
    inputName: null,
    inputPhone: null,
    selectLocation: null,
    selectBases: null,
    btnNext: null,
    selectReason: null,
    containerDesc: null,
    containerComplement: null,
    textDesc: null,
    containerMessage: null,
    inputFile: null,
    containerList: null,
}

var DataFilling = Object.create({
    name: null,
    phone: null,
    location: null,
    base: null,
    reason: null,
    reasonInfo: null,
})

var FilesUpload = {};

var Locations = {
    "BELFORDROXO": ["BASE SAMU", "HMBR", "UPA LOTE XV"],
    "CAXIAS": [
        "BASE SAMU", "CAMPOS ELÍSEOS", "HOSPITAL ADÃO PEREIRA NUNES", "HOSPITAL MOACYR RODRIGUES",
        "UPA INFANTIL WALTER GARCIA", "UPA PARQUE LAFAIETE", "UPA SARAPUI", "UPH IMBARIÊ", "UPH SARACURUNA",
        "XERÉM"
    ],
    "CENTRAL SAMU": false,
    "GOVBR": false,
    "ITAGUAÍ": ["BASE SAMU", "HOSPITAL SÃO FRANSCISCO XAVIER", "UPA DE ITAGUAÍ"],
    "JAPERI": ["BASE SAMU", "HOSPITAL MUNICIPAL DE JAPERI", "POLICLÍNICA ITÁLIA FRANCA"],
    "MAGÉ": [
            "BASE SAMU", "HOSP MAT INF HUGO BRAGA", "HOSPITAL DE MAGÉ", "POSTO 24H MAUÁ", "POSTO 24H MAUÁ",
            "POSTO 24H SANTO ALEIXO", "POSTO 24H SURUPI", "UNIDADE MISTA DE MAUÁ", "UPA MAGÉ"
            ],
    "MESQUITA": ["BASE SAMU", "SES RJ UPA MESQUITA"],
    "NILOPOLIS": ["APONTADORIA", "BASE SAMU"],
    "NOVA IGUAÇU": ["BASE SAMU", "HGNI", "MARIANA BULHÕES", "UPA BOTAFOGO", "UPA CABUÇU", "UPA COMENDADOR SOARES"],
    "PARACAMBI": ["BASE SAMU", "HOSPITAL MUNICIPAL PARACAMBI"],
    "QUEIMADOS": ["BASE SAMU", "CENTRO DE TRIAGEM", "UPA DE QUEIMADOS"],
    "SÃO JOÃO DE MERITI": ["BASE SAMU", "HOSPITAL ABDON GONÇALVES", "UPA JARDIM ÍRIS"],
    "CISBAF": ["RH", "LICITAÇÃO", "CONTABILIDADE", "ALMOXARIFADO", "TI", "COMUNICAÇÃO", "CONTROLE INTERNO", "NEP", "JURIDÍCO", "OUTRO"],
    "SEROPÉDICA": ["BASE SAMU", "UPA SEROPÉDICA", "UPH DR. JOSÉ BUENO LOPES"],
    "UNIDADE MISTA DE SURUÍ": false,
    "UPA JARDM ÍRIS": false
}

var Reasons = {
    "Suporte Computador": null,
    "Suporte Impressora": null,
    "Suporte Sistemas": ["Suporte SSO", "Suporte Marque Fácil", "Plataforma de Ensino NEP", "Outro"],
    "Suporte Tablet": null,
    "Suporte Celular": null,
    "Criação de Login": {
        "Sistemas SSO": ["Nome Completo", "CPF", "Cargo"],
        "Sistema Marque Fácil": ["Nome Completo", "CPF", "Cargo", "Email", "Municipio"]
    },
    "Requisição de Material": null,
    "Convocação para o site": null
}

function InsertOptions(element, options) {
    options.forEach(location=>{
        const option = document.createElement("option");
        option.value = location;
        option.innerHTML = location;
        element.appendChild(option);
    })
}

function SetValueInput(element, value) {
    element.value = value;
}

function SetValueSelect(element, value) {
    if(!value) return;
    const options = [];
    for (let option of element.options) {
        options.push(option.value);
    }
    const index = options.findIndex(v => v === value);
    if (!index) return;
    element.selectedIndex = index;
    element.dispatchEvent(new Event("change"));
}

function FixPhoneNumber(number) {
    return number.replace(/[^\d]/g, '');
}

function MakeMessage(type, text) {
    const alertDiv = document.createElement("div");
    alertDiv.classList.add("alert", `alert-${type}`, "fade-in"); // Adiciona fade-in
    alertDiv.setAttribute("role", "alert");
    alertDiv.textContent = text;
    return alertDiv;
}

function RegisterMessage(type, text) {
    const messageDiv = MakeMessage(type, text);
    elements.containerMessage.appendChild(messageDiv);

    setTimeout(() => {
        messageDiv.classList.add("show");
    }, 10);

    setTimeout(() => {
        messageDiv.classList.remove("show");
        messageDiv.classList.add("fade-out");
        setTimeout(() => {
            messageDiv.remove();
        }, 500);
    }, 5000);
}

window.addEventListener("load", function (event) {
    StepperComponent = new Stepper(document.querySelector('.bs-stepper'));
    elements.containerMessage = document.getElementById("containerMessage");
});