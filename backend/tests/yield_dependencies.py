"""Call a FastAPI dependency that uses ``yield`` outside a request.

The AI quota charges before its ``yield`` and refunds after it when the
request failed without reaching the model (#798), so calling it is no longer
one ``await``. Unit tests that count charges want "a request that went
through": run to the yield, then finish cleanly.
"""


def completes(dependency):
    """``dependency`` as an awaitable that behaves like a request that succeeded.

    An over-cap refusal is raised from the first step, exactly as in a request.
    """

    async def call(*args, **kwargs):
        generator = dependency(*args, **kwargs)
        await generator.__anext__()
        await generator.aclose()

    return call
