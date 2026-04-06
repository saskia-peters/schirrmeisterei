from fastapi import HTTPException, status


class TicketSystemException(HTTPException):
    """Base exception for ticket system."""


class NotFoundException(TicketSystemException):
    def __init__(self, resource: str = "Resource") -> None:
        """Raise a 404 error for the given resource name."""
        super().__init__(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"{resource} not found",
        )


class ForbiddenException(TicketSystemException):
    def __init__(self, detail: str = "Not enough permissions") -> None:
        """Raise a 403 Forbidden error with the given detail message."""
        super().__init__(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=detail,
        )


class UnauthorizedException(TicketSystemException):
    def __init__(self, detail: str = "Could not validate credentials") -> None:
        """Raise a 401 Unauthorized error, prompting Bearer authentication."""
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"},
        )


class ConflictException(TicketSystemException):
    def __init__(self, detail: str = "Resource already exists") -> None:
        """Raise a 409 Conflict error with the given detail message."""
        super().__init__(
            status_code=status.HTTP_409_CONFLICT,
            detail=detail,
        )


class ValidationException(TicketSystemException):
    def __init__(self, detail: str = "Validation error") -> None:
        """Raise a 422 Unprocessable Content error with the given detail message."""
        super().__init__(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=detail,
        )
