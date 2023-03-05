#!/usr/bin/env python3
import json
import yaml

from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = PROJECT_DIR.joinpath('static')
SETTINGS_DIR = STATIC_DIR.joinpath('settings')

SETTINGS_YML = Path(r'C:\ebagis\desktop_settings.yaml')


def main():
    SETTINGS_DIR.mkdir(exist_ok=True)
    
    # encoding seems to be UTF-8 with Byte Order Marking (BOM)
    # https://stackoverflow.com/questions/34399172/why-does-my-python-code-print-the-extra-characters-%C3%AF-when-reading-from-a-tex
    settings = yaml.safe_load(SETTINGS_YML.read_text(encoding='utf-8-sig'))
    for app, app_settings in settings.items():
        settings_json = SETTINGS_DIR.joinpath(f'{app}.json')
        settings_json.write_text(json.dumps(app_settings))


if __name__ == '__main__':
    main()
