from helpers.glpi_controller import DatasRegister

def make_message_group(data: DatasRegister, protocolo: str, anexos: int):
    return f"""
        *CHAMADO TESTE*
        Protocolo: {protocolo} | {data.desc} | Anexos {anexos}
    """