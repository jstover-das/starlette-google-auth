from starlette.config import Config
from starlette.datastructures import Secret

config = Config()

DEBUG = config('DEBUG', cast=bool, default=False)

SECRET_KEY = config('SECRET_KEY', cast=Secret)

REPORTS_BUCKET = config('REPORTS_BUCKET', default='qa.etl.farm')
PLATFORM_RESULTS_TABLE_NAME = config('RESULTS_TABLE_NAME', default='etl-autoqa-results')
HULLSCRUBBER_RESULTS_TABLE_NAME = config('HULLSCRUBBER_RESULTS_TABLE_NAME', default='etl-hullscrubber-qa-results')
