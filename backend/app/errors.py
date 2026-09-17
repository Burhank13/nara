from fastapi import HTTPException


def api_error(status_code: int, code: str, message: str, **extra: object) -> HTTPException:
    """Errors carry a stable machine-readable `code` so the UI can branch on them.

    `extra` adds facts the UI needs to explain the refusal, such as how far away the phone was.
    """
    return HTTPException(status_code=status_code, detail={"code": code, "message": message, **extra})
