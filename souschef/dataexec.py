# usage : python dataexec.py [santropolFeast.settingsSPECIAL]
import os
import sys


def run():
    settings = "souschef.sous_chef.settings"
    if len(sys.argv) > 1:
        settings = sys.argv[1]
    os.environ["DJANGO_SETTINGS_MODULE"] = settings
    import django

    django.setup()
    from dataload import insert_all

    insert_all()


run()
