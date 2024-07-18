# FastAPI structured logs

Provides a wrapper over the structlog for additional
doping in json format, as well as output of standard
logs to the console, configuration via `.env` files
via pedantic.

In addition, middleware and a `sentry` configuration
are available for use in FastAPI applications.

## Installation

You can use `poetry`:

```bash
pip install fastapi-structlog
```

or `pip`:

```bash
poetry add fastapi-structlog
```

## Using logging

To implement logging into the application, it is
enough to use `init_logging`:

```python
import structlog
from fastapi_structlog import init_logger

init_logger()

log = structlog.get_logger()

log.info('Hello, World!')
```

In this case, the entire configuration is taken from
the `.env` file by means of Pedantic.

To use the library in the minimum version, see
example №1 (`docs_src/example_1.py`).

## Logger configuration

To configure the logger, you need to use `fastapi_structlog.init_logging`,
which gets the values of the environment variables using `pydantic`.
You can specify the `env_prefix` argument when using prefixes.

Logger configuration parameters:

- Name of the logger (`LOGGER`), default `default`
- Logging level (`LOG_LEVEL`), default `INFO`
- Flag that activates logging in json format (`JSON_LOGS`), default `True`
- Logging of the traceback in string form (`TRACEBACK_AS_STR`), default `True`
- The name of the file (`FILENAME`), default `None`
- The interval of writing to the file (`WHEN`), one of the `S`, `M`, `H`, `D`, `W`,
default `D` (see [TimedRotatingFileHandler](https://docs.python.org/3/library/logging.handlers.html#timedrotatingfilehandler))
- The number of saved files (`BACKUP_COUNT`), default `1`
(see [TimedRotatingFileHandler](https://docs.python.org/3/library/logging.handlers.html#timedrotatingfilehandler))
- Activate DEBUG mode (`DEBUG`), default `False`
- New name for the key `event` (`EVENT_KEY`), default `message`
(see [renaming the `event` key](https://www.structlog.org/en/stable/recipes.html#renaming-the-event-key))
- Enable logging (`ENABLE`), default `False`
- Methods for logging (`METHODS`), default `["get","delete","post","put","patch","options","head"]`
- Types of logging (`TYPES`), one of the `console`, `internal`, `syslog`, `file`, default `["console"]`
- Number of days to store the log entry (`TTL`), default `90`

Syslog configuration parameters:

- Syslog server address (`SYSLOG__HOST`), default `None`
- Syslog server port (`SYSLOG__PORT`), default `6514`

Database configuration parameters:

- Use async mode (`DB__IS_ASYNC`), default `True`
- Database connection string (`DB__URL`), default `None`
- Database user (`DB__USER`), default `postgres`
- Database password (`DB__PASSWORD`), default `None`
- Database host (`DB__HOST`), default `localhost`
- Database port (`DB__PORT`), default `5432`
- Database name (`DB__NAME`), default `postgres`

When using `fastapi_structlog.setup_logger`, the settings must be
passed manually. An instance of the `LogSettings` class must be
passed as an argument. You can import:

```python
from fastapi_structlog import LogSettings
```

This may be convenient in case of expanding the settings.

The implementation of logging settings allows you to use it in
existing service settings in the form of `pydantic` models.
Just add another field to your settings. You can use `BaseSettingsModel`
as a base class for your settings. This class already includes the basic
configuration, for example:

- delimiter as `__`
- ignoring environment variables with empty values

```python
import structlog
from fastapi_structlog import LogSettings, setup_logger, BaseSettingsModel

logger = structlog.get_logger()

class Settings(BaseSettingsModel):
    log: LogSettings

    model_config = SettingsConfigDict(
        secrets_dir="/run/secrets" if Path("/run/secrets").exists() else None,
    )


def main() -> None:
    settings = Settings()

    setup_logging(**settings.log.model_dump())


if __name__ == "__main__":
    main()
```

For more information about the integration of logging
settings, see example №4 (`docs_src/example_4.py`).

## Using logging in a FastAPI application

The use of the library in FasAPI application is for the most part
similar to that described in the section
["Logger configuration"](#logger-configuration). To embed it into
your application, it is enough in the `main` function of the file
`main.py` (or any other entry point) before starting `uvicorn` (or
another server), use one of the logger configuration functions. In
all other places, it is enough to use `structlog.get_logger(log_name)`
to get the logger. It will be configured according to the settings
specified when launching the application.

For more information about integrating logging into a FasAPI
application, see example №2 (`docs_src/example_2.py`).

## Using middleware in a FastAPI application

The library provides the following middleware:

- `fastapi_structlog.middleware.CurrentScopeSetMiddleware` - Creating
the current context
- `fastapi_structlog.middleware.StructlogMiddleware` - Adds a
pass-through request ID to the logs context. It should be used
together with `asgi_correlation_id.middleware.CorrelationIdMiddleware`
([github](https://github.com/snok/asgi-correlation-id)) or other
middleware for generating end-to-end IDs.
- `fastapi_structlog.middleware.AccessLogMiddleware` - Allows you
to keep a log of access to the service.

You can add this middleware to a FasAPI application as follows:

```python
app = FastAPI(
    title="Example API",
    version="1.0.0",
    middleware=[
        Middleware(CurrentScopeSetMiddleware),
        Middleware(CorrelationIdMiddleware),
        Middleware(StructlogMiddleware),
        Middleware(AccessLogMiddleware),
    ],
)
```

It's worth noting that `CurrentScopeSetMiddleware` should come
first, and `StructlogMiddleware` after `CorrelationIdMiddleware`!

In order for `AccessLogMiddleware` to use `structlog`, you need
to initialize the logger before starting uvicorn (or another server).
Otherwise, the standard logger will be used, which will be reported
in the corresponding warning.

For more information about integrating logging into a FasAPI
application, see example №5 (`docs_src/example_5.py`).

### Logging format

The `AccessLogMiddleware` middleware allows the use of the following parameters:

Name          | Alternative    | Description
--------------|----------------|--------------------------------------
`h`           | `client_addr`  | Client address (`IP:PORT`)
`r`           |                | A query string indicating the type of request and the protocol version in the format `method path protocol`
`R`           | `request_line` | Similar to the previous one, the format `method full_path protocol`, includes query parameters
`t`           |                | Time
`m`           |                | Method
`U`           |                | URL
`q`           |                | Query parameters
`H`           |                | Protocol
`s`           |                | Status
`st`          |                | Name of the status
`status_code` |                | Status in the format `status name`
`B`           | `b`            | [`Content-Length`](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Content-Length)
`f`           |                | [`Referer`](https://developer.mozilla.org/ru/docs/Web/HTTP/Headers/Referer)
`a`           |                | [`User-Agent`](https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/User-Agent)
`T`           |                | Request time (integer number of seconds)
`M`           |                | Request time (integer number of seconds * 1000)
`D`           |                | Request time (integer number of seconds * 1_000_000)
`L`           |                | Request time (seconds with 6 decimal places)
`p`           |                | Process ID
`l`           |                | -
`u`           |                | -
`session`     |                | User session data

Using any parameter requires the inclusion of an expression
in the format string `%(PARAM_NAME)s`.

The following format is used by default:

```python
%(client_addr)s - "%(request_line)s" %(status_code)s %(L)ss - "%(a)s"
```

## Using Sentry in a FastAPI application

Using Sentry is completely similar to using logging. You can use
`fastapi_structlog.sentry.init_sentry` (with the `env_prefix` parameter)
to configure Sentry using the built-in model
(`fastapi_structlog.sentry.SentrySettings`) settings. In this case,
the parameters will be taken from the environment variables via
`pydantic`. If necessary, you can specify `release`, `app_slug`
and `version`. These parameters will be used when generating the
`release` parameter for transmission to Sentry. The release is
formed either from the explicitly passed `release` argument or
in the `app_slug@version` format.

Another Sentry configuration option is to use
`fastapi_structlog.sentry.setup_sentry`. However, in this case,
you must explicitly pass an instance of the settings
`fastapi_structlog.sentry.SentrySettings` and the `release` parameter.

The Sentry configuration parameters are as follows:

- `dsn` - [Name of the data source](https://docs.sentry.io/product/sentry-basics/concepts/dsn-explainer/)
- `env` - The name of the environment, see `fastapi_structlog.sentry.Environment`
- `traces_sample_rate` - [Uniform sampling rate](https://docs.sentry.io/platforms/python/configuration/sampling/#configuring-the-transaction-sample-rate)
- `log_integration` - Flag for using logging integration, by default `True`.
For more information, see [sentry docs](https://docs.sentry.io/platforms/python/integrations/logging/).
- `log_integration_event_level` - Parameter `event_level` for `LoggingIntegration`, by default `None`.
- `log_integration_level` -  - Parameter `level` for `LoggingIntegration`, by default `None`.
- `sql_integration` - Flag for using
[SQLAlchemy integration](https://docs.sentry.io/platforms/python/integrations/sqlalchemy/),
by default `True`.

By inheriting from `fastapi_structlog.sentry.SentrySettings`, you can
extend the Sentry configuration by adding the necessary
[parameters](https://docs.sentry.io/platforms/python/configuration/options/)
(see example №7 (`docs_src/example_7.py`).).

All parameters are optional! If there is no `dsn` Sentry will be ignored!

The implementation of Sentry settings in the settings of the general
project is similar to the one described in the section
["Logger configuration"](#logger-configuration).

For more information about integrating Sentry into the FasAPI
application, see example №3 (`docs_src/example_3.py`).

To use `sentry_sdk` with requests to other APIs, see example №6 (`docs_src/example_6.py`).

In addition, both functions accept the `service_integration` parameter.
This parameter is intended for inter-service interaction and can be
useful for repeated requests (for example, to track the delay before
a repeat request, to track subqueries to other services, to monitor
the time for data serialization, and more).

## Logging into the database

If you want to save logs to a database, then you need to declare a table
model. The library provides a basic `LogModel` model that you can import as:

```python
from fastapi_structlog.db_handler import LogModel
```

This model inherits SQLModel and is a **data model**, that is, it does
not have the `table=True` parameter. Therefore, you need to make a class
that will inherit this model and add `table=True`. You can also add new
fields or write your own model altogether. However, the `fastapi_structlog`
relies on it to be the Inheritor of the `SQLModel`:

```python
class Log(LogModel, table=True):
    """Log table."""
```

You should use one of the logger initialization functions and pass
your model there, as well as the database connection string. This may be
a different database from your main one.

```python
engine = create_async_engine(DB_URL)

queue_listener = init_logger(
    env_prefix='LOG__',
    model=Log,
    db_url=DB_URL,
)

logger = structlog.get_logger()
```

Use `lifespan` to start and stop `queue_listener`, for example:

```python
@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None, None]:
    async with engine.begin() as conn:
        await conn.run_sync(Log.metadata.create_all)

    if queue_listener:
        queue_listener.start()

    yield

    if queue_listener:
        queue_listener.stop()
```

You must pass `lifespan` as a parameter to the `FastAPI` class. This is the
end of logging into the database.

You can read the sample code in `docs_src/example_8.py`

## Examples

For other usage docs_src, see `docs_src`:

- `example_1` - simple example
- `example_2` - example using `fastapi` and `uvicorn`
- `example_3` - example using `fastapi`, `uvicorn` and `sentry`
- `example_4` - example with the integration of logging settings into the application settings
- `example_5` - example using middleware
- `example_6` - example using Sentry and nested calls to other APIs

## Dependencies

The following dependencies are used here:

- Python 3.9
- pydantic (for validate the settings)
- structlog (for set up the logger)
- sentry_sdk
- SQLModel (for database integration)
