

function makeRadioButton(text) {
    return `
    <div class="form-check">
        <input class="form-check-input" value="${text}" type="radio" name="radiosReason" id="radio${text}">
        <label class="form-check-label" for="radio${text}">
            ${text}
        </label>
    </div>`;
}

function makeInput(text) {
    return `
    <div class="mb-3">
        <label for="input${text}" class="form-label">${text}</label>
        <input type="text" name="inputsReason" data-target="${text}" class="form-control" id="input${text}">
    </div>`
}

function handleCategory(e, object, original) {
    var swap = "";
    for(let category of object) {
        swap += makeInput(category);
    }
    createCategory(original, swap, e.target.value);
}

function createCategory(object, append=false, selected=false) {
    var radios = "";
    Object.keys(object).forEach(category=>{
        radios += makeRadioButton(category);
    });
    if (append) {
        radios += append;
    }
    elements.containerComplement.innerHTML = radios;
    Object.keys(object).forEach(category=>{
        const rb = document.getElementById(`radio${category}`);
        if (selected == category) {
            rb.checked = true;
        }
        rb.addEventListener("change", (e)=>handleCategory(e, object[category], object));
    })
}

function createOptions(options) {
    var radios = "";
    for(let option of options) {
        radios += makeRadioButton(option);
    }
    elements.containerComplement.innerHTML = radios;
}


function handleReason(e){
    const select = e.target;
    const values = Reasons[select.value];
    elements.containerComplement.innerHTML = "";
    if (values) {
        if (!(Array.isArray(values))){
            createCategory(values);
            elements.containerDesc.style.display = "none";
        } else {
            createOptions(values);
            elements.containerDesc.style.display = "";
        }
    } else {
        elements.containerDesc.style.display = "";
    }
}

function validateStepReason() {
    try {
        const valueSelected = Reasons[elements.selectReason.value];
        DataFilling.reason = elements.selectReason.value;
        if (!valueSelected) {
            const valueDesc = elements.textDesc.value;
            if (valueDesc.length < 1) throw new Error("Preencha o campo Descrição!");
            DataFilling.reasonInfo = valueDesc;
        } else {
            const radiosReason = Array.from(document.getElementsByName("radiosReason"));
            const valueRadio = radiosReason.find(input=>input.checked === true);
            if (!valueRadio) throw new Error("Marque uma opção!");
            if (!(Array.isArray(valueSelected))){
                const inputsReason = Array.from(document.getElementsByName("inputsReason"));
                var valueInputs = "";
                inputsReason.forEach((input, i)=>{
                    const field = input.getAttribute("data-target");
                    const inputValue = input.value;
                    if(inputValue.length < 1) throw new Error(`Preencha o campo ${field}`);
                    valueInputs += `${field}: ${inputValue}`;
                    if (i != inputsReason.length - 1) {
                        valueInputs += " | ";
                    }
                });
                DataFilling.reasonInfo = `${valueRadio.value} -> ${valueInputs}`;
            } else {
                const valueDesc = elements.textDesc.value;
                if (valueDesc.length < 1) throw new Error("Preencha o campo Descrição!");
                DataFilling.reasonInfo = `${valueRadio.value} -> ${valueDesc}`;
            }
        }
        StepperComponent.next();   
    } catch (e) {
        RegisterMessage("danger", e.message);
        console.log(e);
    }

}

window.addEventListener("load", function (event) {
    elements.selectReason = document.getElementById("selectReason");
    elements.selectReason.addEventListener("change", handleReason);
    elements.containerDesc = document.getElementById("containerDesc");
    elements.containerComplement = document.getElementById("containerComplement");
    elements.textDesc = document.getElementById("textDesc");
    InsertOptions(elements.selectReason, Object.keys(Reasons));
});