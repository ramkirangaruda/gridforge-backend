from werkzeug.utils import secure_filename as werkzeug_secure_filename

def secure_filename(filename: str) -> str:
    """
    Sanitizes a filename to prevent directory traversal attacks and invalid characters.
    """
    # Use werkzeug's implementation which is robust
    filename = werkzeug_secure_filename(filename)
    # Additional paranoid check
    if ".." in filename or "/" in filename:
        return "invalid_filename"
    return filename
