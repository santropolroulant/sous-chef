import os
import time

from django.conf import settings


def clean_old_pdf_files():
    now = time.time()
    a_year = 356 * 24 * 60 * 60
    for filename in os.listdir(settings.GENERATED_DOCS_DIR):
        file_path = os.path.join(settings.GENERATED_DOCS_DIR, filename)
        if '.pdf' in filename and os.path.getmtime(file_path) < now - a_year:
            if os.path.isfile(file_path):
                os.remove(file_path)
