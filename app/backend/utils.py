import logging
import tempfile
import uuid
from pathlib import Path

from pymongo import errors as pymongo_errors

from app.backend.accessors import get_collection
from app.backend.config import get_config_variables

LOG = logging.getLogger(__name__)

CONFIG = get_config_variables()


def load_memory_to_pass(session_id: str) -> list[tuple[str, str]]:
    """Load the memory history for a given session ID.

    This function retrieves the conversation history from the MongoDB
        collection and formats it for use in the chat.

    Args:
        session_id (str): The session ID to load memory for.

    Returns:
        list: The loaded memory history.

    """
    data = get_collection().find_one({"session_id": session_id})
    history = []

    if data:
        data = data["conversion"]

        for x in range(0, len(data), 2):
            history.extend([(data[x], data[x + 1])])

    LOG.info(history)

    return history


def get_session() -> str:
    """Generate a new session ID.

    This function generates a new session ID for the chat.

    Returns:
        str: The generated session ID.

    """
    return str(uuid.uuid4())


def add_session_history(session_id: str, new_values: list[str]) -> bool:
    """Add a new session history entry.

    This function adds a new entry to the chat history in the MongoDB
        collection.

    Args:
        session_id (str): The session ID for the chat.
        new_values (list): The new values to be added to the conversation history.

    Returns:
        bool: True if the entry was added successfully, False otherwise.

    """
    try:
        doc = get_collection().find_one({"session_id": session_id})

        if doc:
            conversion = doc["conversion"]
            conversion.extend(new_values)
            get_collection().update_one(
                {"session_id": session_id},
                {"$set": {"conversion": conversion}},
            )
        else:
            get_collection().insert_one(
                {
                    "session_id": session_id,
                    "conversion": new_values,
                }
            )
    except pymongo_errors.PyMongoError as e:
        message = str(e)
        LOG.exception(f"Error adding session history: {message}")
        return False
    else:
        return True


def get_temp_file_path(filename: str | None) -> Path:
    """Validate filename and prepare a temporary file path.

    Args:
        filename: The original filename from the upload

    Returns:
        Path: Path object pointing to the temporary file location

    Raises:
        FileNotFoundError: If the filename is None

    """
    if filename is None:
        msg = "Uploaded file must have a filename."
        raise FileNotFoundError(msg)

    # Create a safe filename without potentially problematic characters
    safe_filename = Path(filename).name

    # Create path in secure temporary directory
    tmp_path = Path(tempfile.gettempdir()) / safe_filename

    LOG.info(f"Using temporary file path: {tmp_path}")

    return tmp_path
