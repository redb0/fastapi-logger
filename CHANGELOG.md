## 0.5.0 (2024-09-18)

### Feat

- **sentry**: Added the ability to customize failed status codes during Sentry setup.

### Fix

- **sentry**: fix typing

## 0.4.5 (2024-08-30)

### Fix

- **middleware**: fix get api source

## 0.4.4 (2024-08-20)

### Fix

- **all**: hide password in log
- **access_log**: fix argument passing
- **middleware**: adding custom attribute search functions
- **middleware**: add request when scope type is http

## 0.4.3 (2024-08-13)

### Fix

- **da-handler**: fix connection error

## 0.4.2 (2024-08-13)

### Fix

- **middleware**: fix get key error
- **log**: add logger name filter
- allow newer sqlmodel version

## 0.4.1 (2024-08-02)

### Fix

- **all**: fix validation

## 0.4.0 (2024-08-02)

### Feat

- **db_handler**: Added parameters for universal attribute search

## 0.3.7 (2024-07-31)

### Fix

- **db-handler**: fix get level and logger name

## 0.3.6 (2024-07-31)

### Fix

- **db-handler**: fix get logger name and level

## 0.3.5 (2024-07-31)

### Fix

- **all**: add logger name, level in model, message chenge to json

## 0.3.4 (2024-07-22)

### Fix

- **settings**: refactor settings

## 0.3.3 (2024-07-19)

### Fix

- **typing**: fix py.typed

## 0.3.2 (2024-07-19)

### Fix

- **typing**: add py.typed

## 0.3.1 (2024-07-18)

### Fix

- **base**: ignore extra field

## 0.3.0 (2024-07-18)

### Feat

- **base**: Rename _BaseModel -> BaseSettingsModel
- **sentry**: Add warning for missing dsn

## 0.2.0 (2024-07-17)

### Feat

- **sentry**: Add sentry integration
- **middleware**: Add logging middleware
- **db_handler**: Add database handler
- **all**: downgraded python version to 3.9
