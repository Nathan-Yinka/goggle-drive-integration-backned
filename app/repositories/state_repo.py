import redis
import logging
from app.config import REDIS_URL

logger = logging.getLogger(__name__)

# Initialize Redis
redis_client = redis.from_url(REDIS_URL, decode_responses=True)

def save_state(state: str, user_id: str, expiry: int = 300):
    """
    Stores the OAuth state for a user with a time limit.
    """
    try:
        redis_client.setex(f"oauth_state:{state}", expiry, user_id)
    except Exception as e:
        logger.error(f"Error saving OAuth state: {e}")

def get_user_id_by_state(state: str):
    """
    Retrieves user_id associated with the OAuth state.
    """
    try:
        return redis_client.get(f"oauth_state:{state}")
    except Exception as e:
        logger.error(f"Error retrieving user_id from state: {e}")
        return None

def delete_state(state: str):
    """
    Removes the OAuth state after it's used.
    """
    try:
        redis_client.delete(f"oauth_state:{state}")
    except Exception as e:
        logger.error(f"Error deleting OAuth state: {e}")
