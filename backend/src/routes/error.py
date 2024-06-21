from fastapi import Depends, logger
from fastapi.templating import Jinja2Templates

from backend.src.dependencies import get_templates


def error(
    message: str,
    exception: Exception | None = None,
    request=None,
    templates: Jinja2Templates = Depends(get_templates),
):
    logger.error(f"{message}")
    if exception:
        logger.error(f"Exception: {exception}")
        logger.error(f"Traceback: {traceback.format_exc()}")
    if request:
        return templates.TemplateResponse(
            name="error.html",
            request=request,
            context={"error_message": message},
        )
