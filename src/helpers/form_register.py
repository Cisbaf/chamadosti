from helpers.glpi_controller import DatasRegister

fields = ['name', 'phone', 'location', 'reason', 'reasonInfo']

def rename(name):
    return f'-{name}'

def validate_form(data: dict):
    for field in fields:
        if not data.get(field):
            raise Exception(f"Campo {field} não encontrado.")
    return DatasRegister(
        unity=f"{data.get('location')}{rename(data.get('base')) if data.get('base') else ""}",
        reason=data.get('reason'),
        desc=f"Solicitante: {data.get('name')} | Unidade: {data.get('location')} | Solicita: {data.get('reason')} | Motivo: {data.get('reasonInfo')} | Contato: {data.get('phone')} ",
        contact=data.get('phone')
    )
