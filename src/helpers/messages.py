from helpers.glpi_controller import DatasRegister

def make_message_group(data: DatasRegister, protocolo: str, anexos: int):
    return f"""*NOVA ABERTURA DE CHAMADO!*
Protocolo: {protocolo} | {data.desc} | Anexos {anexos}
"""