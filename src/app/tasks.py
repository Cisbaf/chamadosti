import requests, os
from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from helpers.glpi_controller import Archive, GLPIFunctions, ChromeDriverController
from helpers.form_register import validate_form
from helpers.messages import make_message_group
from helpers.protocol import generate_protocol
from helpers.security_imgs import register_images
from dotenv import load_dotenv

load_dotenv(override=True)

@shared_task(bind=True, max_retries=10, retry_delay=30)
def task_notification_wpp(self, number: str, message: str):
    API_NOTIFICATION_URL = os.getenv("API_NOTIFICATION_URL")
    data = {
        "number": number,
        "message": message,
        "is_group": False,
    }
    try:
        response = requests.post(API_NOTIFICATION_URL, json=data)
        response_message = response.json()['message']
        if response.status_code == 200:
            return response_message
        else:
            raise Exception(response_message)
    except Exception as exc:
        self.retry(exc=exc)

@shared_task(bind=True, max_retries=3, default_retry_delay=10)
def glpi_register(self, data: dict, archives: dict):
    CONTACT_NOTIFICATION = os.getenv("CONTACT_NOTIFICATION")
    driver = ChromeDriverController(hadless=True, cache=False)
    try:
        # Validação e registro
        data_register = validate_form(data)
        protocol = generate_protocol(8)
        files = []
        if archives:
            for name, file in archives.items():
                files.append(Archive(
                    name, file
                ))
            register_images(self.request.id, files)
        glpi = GLPIFunctions(driver)
        glpi.login()
        glpi.open_request(protocol, data_register, files)
        # Enviar notificações
        task_notification_wpp.delay(
            CONTACT_NOTIFICATION,
            make_message_group(data_register, protocol, len(files))
        )
        task_notification_wpp.delay(
            data_register.contact, 
            f"O seu chamado foi aberto, caso você não tenha retorno, envie o protocolo {protocol} para a equipe de TI"
        )
    except Exception as e:
        try:
            self.retry(exc=e)
        except MaxRetriesExceededError:
            # Notificar falha após exceder o número de tentativas
            task_notification_wpp.delay(
                CONTACT_NOTIFICATION, 
                f"Não foi possível registrar o chamado no GLPI. Task ID: {self.request.id}"
            )
    finally:
        driver.driver.quit()