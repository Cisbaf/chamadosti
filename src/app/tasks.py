import requests, os
from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
from helpers.glpi_controller import Archive, GLPIFunctions, ChromeDriverController
from helpers.form_register import validate_form
from helpers.messages import make_message_group
from helpers.protocol import generate_protocol
from helpers.security_imgs import register_images
from requests.exceptions import ConnectionError, ConnectTimeout

@shared_task(bind=True, max_retries=30, retry_delay=30)
def task_notification_wpp(self, number: str, message: str, is_group=False):
    API_NOTIFICATION_URL = os.getenv("API_NOTIFICATION_URL")
    data = {
        "to": number,
        "message": message,
        "is_group": is_group,
    }
    try:
        response = requests.post(API_NOTIFICATION_URL, json=data)
        response_message = response.json()
        if response.status_code == 200:
            return response_message
        else:
            raise Exception(response_message)
    except ConnectionError as exc:
        self.retry(exc=exc)
    except ChildProcessError as exc:
        self.retry(exc=exc)

@shared_task(bind=True, max_retries=3, default_retry_delay=30)
def glpi_register(self, data: dict, archives: dict):
    CONTACT_NOTIFICATION = os.getenv("CONTACT_NOTIFICATION")
    try:
        # Validação e registro
        driver = ChromeDriverController(cache=False)
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
            make_message_group(data_register, protocol, len(files)),
            True
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