
function MakeFinishMessage(bool) {
    const finishDiv = document.getElementById("finish-part");
    if (bool) {
        finishDiv.innerHTML = `
            <p>Chamado Finalizado com sucesso, aguarde o setor de TI entrar em contato!</p>
            <a href="/">Abrir novo chamado</a>
        `
    } else {
        finishDiv.innerHTML = `
            <p>Ocorreu algum erro ao abrir o chamado, nos avise do problema, para seguirmos manualmente!</p>
        `
    }
    StepperComponent.next();   
}

function SendRequest() {
    return new Promise(async(resolve, reject)=>{
        const form = new FormData();
        form.append("data", JSON.stringify(DataFilling))
        Object.values(FilesUpload).forEach(file=>{
            form.append(`files`, file);
        })
        const request = await fetch('api/register', {
            method: "POST",
            body: form
        });
        if (!request.ok) reject();
        resolve();
    })
}

function FinishRequest() {
    SendRequest().then(()=>{
        RegisterMessage("success", "Chamado Finalizado com sucesso!");
        MakeFinishMessage(true);
    }).catch(()=>{
        RegisterMessage("danger", "Ocorreu um erro ao Finalizar o chamado!");
        MakeFinishMessage(false);
    })
}