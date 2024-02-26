# import logging
# import sentry_sdk
# from sentry_sdk.integrations.logging import LoggingIntegration


def init_logging():

    # sentry_logging = LoggingIntegration(
    #     level=logging.INFO,  # Capture info and above as breadcrumbs
    #     event_level=logging.INFO,  # Send info as events
    # )

    # sentry_sdk.init(
    #     dsn="https://06113f16a29491def6a5c439c0ff1803@o4506806255288320.ingest.sentry.io/4506806257516544",
    #     # Set traces_sample_rate to 1.0 to capture 100%
    #     # of transactions for performance monitoring.
    #     traces_sample_rate=1.0,
    #     # Set profiles_sample_rate to 1.0 to profile 100%
    #     # of sampled transactions.
    #     # We recommend adjusting this value in production.
    #     profiles_sample_rate=1.0,
    #     integrations=[sentry_logging],
    # )
    pass
