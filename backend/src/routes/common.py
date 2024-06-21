import traceback

from utils import get_logger

logger = get_logger(__file__)


def show_error(
    message: str, exception: Exception | None = None, request=None, templates=None
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
