

function calculateFiles(newFile, maxSize) {
    var totalSize = newFile.size;
    Object.values(FilesUpload).forEach(file=>{
        totalSize += file.size;
    })
    if (totalSize > maxSize) {
        return false;
    }
    return true;
}


function createButtom() {
    const btn = document.createElement("button");
    btn.classList.add("btn");
    btn.classList.add("btn-danger");
    btn.innerHTML = "Remover";
    return btn;
}

function removeItemList(fileName, listItem) {
    listItem.remove();
    delete FilesUpload[fileName];
    console.log("newitems", FilesUpload);
}

function createItemList(fileName) {

    const listItem = document.createElement("li");
    listItem.classList.add("list-group-item");
    const divItem = document.createElement("div");
    divItem.classList.add("list-group-flex");
    const label = document.createElement("label");
    label.innerHTML = fileName;
    const btn = createButtom();
    btn.addEventListener("click", ()=>removeItemList(fileName, listItem));
    divItem.appendChild(label);
    divItem.appendChild(btn);
    listItem.appendChild(divItem);
    return listItem;
}

function createRepresentation(fileName) {
    elements.containerList.appendChild(createItemList(fileName));
}

function loadFile(e) {
    const inputFile = e.target;
    const fileList = inputFile.files; // Obtenha os arquivos selecionados
    if (Object.keys(FilesUpload).length >= 2){
        RegisterMessage("danger", "Limite de dois arquivos!")
        return;
    }else {
        for (const file of fileList) {
   
            if(calculateFiles(file, 2097152)){
                FilesUpload[file.name] = file; // Armazena o arquivo no dicionário com o nome do arquivo como chave
                createRepresentation(file.name);
                RegisterMessage("success", "Arquivo adicionado!")
            } else {
                RegisterMessage("danger", "O(s) tamanho(s) do arquivo(s), ultrapassam 2mb!")
            }
    
        }
    }
    inputFile.value = "";
    console.log(FilesUpload);
}

window.addEventListener("load", function (event) {
    elements.inputFile = document.getElementById("inputFile");
    elements.inputFile.addEventListener("input", loadFile);
    elements.containerList = document.getElementById("containerList");
});