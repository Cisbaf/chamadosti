from helpers.glpi_controller import Archive
from typing import List

def register_images(taskID, archives: List[Archive]):
    for archive in archives:
        with open(f"temp/{taskID}-{archive.name}", "wb") as file:
            file.write(archive.bts)