import os

import structlog

from fastapi_structlog import init_logger

os.environ['LOG__LOGGER'] = 'test-log-lib'
# Writing to the console, disabling json mode
os.environ['LOG__JSON_LOGS'] = 'False'
# Activate debugging mode
os.environ['LOG__DEBUG'] = 'True'
os.environ['LOG__TYPES'] = '["console"]'

init_logger(env_prefix='LOG__')

log = structlog.get_logger()

def main() -> None:
    try:
        print(f'{1 / 0 = }')
    except ZeroDivisionError:
        log.exception('Error')


if __name__ == '__main__':
    main()
