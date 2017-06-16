# -*- coding: utf-8 -*-

import os, sys
os.environ["DJANGO_SETTINGS_MODULE"] = "settings"

from django.core.management import call_command

if __name__ == "__main__":
    import django
    django.setup()

    args = sys.argv[1:]
    if not args:
        args = ["filtered_contenttypes",]
    call_command("test", *args, verbosity=0, interactive=False)
