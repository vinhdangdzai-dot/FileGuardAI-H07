"""Public Flask application factory (lazy import for standalone ML tests)."""


def create_app(config=None):
    from .web import create_app as factory
    return factory(config)
