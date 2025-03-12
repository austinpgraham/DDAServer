import logging
from http import HTTPStatus
from django.http import HttpResponse
from ninja import NinjaAPI
from ninja.errors import ValidationError
from dda.v1.routes.http import APIRequest
from dda.v1.routes.http import APIResponse

logger = logging.getLogger("dda")


def handle_general_exceptions(
    request: APIRequest,
    exc: Exception,
    api: NinjaAPI
) -> HttpResponse:
    """
    Exception handler for a general exception that should cause a 500, so we
    can sanitize the response.

    Args:
        request (APIRequest): The originating request.
        exc (Exception): The source exception.
        api (NinjaAPI): The root API object serving this request.

    Returns:
        An HttpResponse containing the error information.
    """
    logger.error(
        f"Request failed with outgoing exception: ${str(exc)}",
        extra=request.state.dict()
    )

    return api.create_response(
        request,
        APIResponse(
            error_code="UnknownError",
            error_message="An unknown error has occurred"
        ).model_dump(by_alias=True),
        status=HTTPStatus.INTERNAL_SERVER_ERROR
    )

def handle_validation_errors(
    request: APIRequest,
    exc: ValidationError,
    api: NinjaAPI
) -> HttpResponse:
    """
    Exception handler for a validation failure of input coming
    into the API.

    Args:
        request (APIRequest): The originating request.
        exc (Exception): The source exception.
        api (NinjaAPI): The root API object serving this request.

    Returns:
        An HttpResponse containing the error information.
    """
    error_location = ["unknown"]
    if len(exc.errors) > 0:
        # Only handle one at a time, this may not be
        # the best way, we can extend later if need be.
        error = exc.errors[0]
        location = error.get("loc", ["unknown"])
        if location:
            error_location = location

    logger.error(
        f"Request failed with a validation error at location {error_location[-1]}",
        extra=request.state.dict()
    )

    return api.create_response(
        request,
        APIResponse(
            error_code="ValidationError",
            error_message=f"Validation failed at field ${error_location[-1]}"
        ).model_dump(by_alias=True),
        status=HTTPStatus.BAD_REQUEST
    )
