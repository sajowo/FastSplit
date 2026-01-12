#!/usr/bin/env python
"""Django's command-line utility for administrative tasks."""
import os
import sys

# Dev-only: jeśli masz problem z SSL na macOS, możesz ustawić
# PYTHONHTTPSVERIFY_DISABLE=1 (nie zalecane poza lokalnym dev)
if os.getenv("PYTHONHTTPSVERIFY_DISABLE") in {"1", "true", "TRUE", "yes", "YES"}:
    os.environ["PYTHONHTTPSVERIFY"] = "0"

def main():
    """Run administrative tasks."""
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'FastSplit.settings')
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == '__main__':
    main()
