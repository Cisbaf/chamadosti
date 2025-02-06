
function RequestGetUserOfNumber(number) {
    return new Promise(async(resolve, reject)=>{
        const url = `users/get_of_number/${number}`;
        const request = await fetch(url);
        if (request.ok) resolve(await request.json());
        reject();
    })
}

function setDisplayInputs(actual, display) {
    for(let div of elements.containerInputs) {
        if (div.style.display == actual){
            div.style.display = display;
        }
    }
}


function checkNumber(e) {
    const input = e.target;
    const value = input.value;
    if (value.length != 14) return;

    const numberPhone = FixPhoneNumber(value);
    RequestGetUserOfNumber(numberPhone)
    .then((response)=>{
        SetValueInput(elements.inputName, response.name);
        SetValueSelect(elements.selectLocation, response.location);
        SetValueSelect(elements.selectBases, response.base);
    })
    .catch((response)=>{

    })
    setDisplayInputs("none", "");
}

function locationSelected(e) {
    const select = e.target;
    const bases = Locations[select.value];
    elements.selectBases.innerHTML = "";
    if (!bases){
        elements.containerBases.style.display = "none";
        return;
    }
    elements.containerBases.style.display = "";
    InsertOptions(elements.selectBases, bases);
}

function validateStepDp() {
    try {
        if (elements.inputName.value.length < 3) throw new Error("Preencha o seu nome completo!");
        if (elements.inputPhone.value.length < 13) throw new Error("Preencha o número do seu celular!");
        DataFilling.name = elements.inputName.value;
        DataFilling.phone = FixPhoneNumber(elements.inputPhone.value);
        DataFilling.location = elements.selectLocation.value;
        if (elements.selectBases.value) {
            DataFilling.base = elements.selectBases.value;
        }
        StepperComponent.next();   
    }
    catch(e){
        RegisterMessage("danger", e.message);
        console.log(e.message);
    }
}

window.addEventListener("load", function (event) {
    elements.containerInputs = document.getElementsByName("containerInputs");
    elements.containerBases = document.getElementById("containerBases");
    elements.inputName = document.getElementById("inputName");
    elements.inputPhone = document.getElementById("inputPhone");
    elements.selectLocation = document.getElementById("selectLocation");
    elements.selectBases = document.getElementById("selectBases");
    elements.btnNext = document.getElementById("btnNext");
    elements.inputPhone.addEventListener("input", checkNumber);
    elements.selectLocation.addEventListener("change", locationSelected);
    setDisplayInputs("", "none");
    InsertOptions(elements.selectLocation, Object.keys(Locations));
    $('#inputPhone').mask('(00)00000-0000');
})