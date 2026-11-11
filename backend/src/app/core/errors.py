from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

from app.core.contracts import Problem


class ApplicationError(Exception):
    def __init__(self, status: int, code: str, title: str):
        self.status, self.code, self.title = status, code, title


def problem_response(request: Request, status: int, code: str, title: str) -> JSONResponse:
    # Never reflect arbitrary paths, input values, exception strings or query strings.
    route = getattr(request.scope.get("route"), "path", "/")
    problem = Problem(
        title=title,
        status=status,
        detail=title,
        instance=route,
        code=code,
        request_id=request.state.request_id,
    )
    return JSONResponse(
        problem.model_dump(), status_code=status, media_type="application/problem+json"
    )


def install_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(ApplicationError)
    async def application_error(request: Request, error: ApplicationError) -> JSONResponse:
        return problem_response(request, error.status, error.code, error.title)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, error: RequestValidationError) -> JSONResponse:
        return problem_response(request, 422, "validation_error", "Invalid request")

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, error: HTTPException) -> JSONResponse:
        titles = {404: "Resource not found", 405: "Method not allowed"}
        return problem_response(
            request,
            error.status_code,
            f"http_{error.status_code}",
            titles.get(error.status_code, "Request rejected"),
        )

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, error: Exception) -> JSONResponse:
        return problem_response(request, 500, "internal_error", "Unexpected error")
