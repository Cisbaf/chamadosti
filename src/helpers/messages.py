from helpers.glpi_controller import DatasRegister

def make_message_group(data: DatasRegister, protocolo: str, anexos: int):
    return f"""*NOVO CHAMADO!*
Protocolo: {protocolo} | {data.desc} | Anexos {anexos}
"""