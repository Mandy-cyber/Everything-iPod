import os
import keyring as kr
from dotenv import load_dotenv
from typing import Optional

from .constants  import SERVICE_NAME

load_dotenv()

def save_credentials(credentials: dict) -> bool:
    """Stores the given credentials in the system keyring

    Args:
        credentials (dict): {
            "last_fm": {
                "api_key": str,
                "shared_secret": str.
            },
        }

    Returns:
        bool: True if successful, False otherwise
    """
    # last_fm
    last_fm: dict = credentials['last_fm']
    
    try:
        kr.set_password(SERVICE_NAME, 'last_fm-api_key', last_fm.get('api_key', ''))
        kr.set_password(SERVICE_NAME, 'last_fm-shared_secret', last_fm.get('shared_secret', ''))
        return True
    except Exception as e:
        print(f"Failed to save credentials in keyring: {e}")
        return False

def get_credentials() -> Optional[dict]:
    """Gets the credentials stores in the system keyring. Fallsback
    to grabbing from the .env if necessary"""
    # last_fm
    creds = {'last_fm': {}}
    
    try:
        # get from keyring
        api_key = kr.get_password(SERVICE_NAME, 'last_fm-api_key')
        shared_secret = kr.get_password(SERVICE_NAME, 'last_fm-shared_secret')
        if api_key is not None and shared_secret is not None:
            creds['last_fm'] = {
                'api_key': api_key,
                'shared_secret': shared_secret
            }
            return creds
        
        # fallback: get from .env
        api_key = os.getenv('LASTFM_API_KEY')
        shared_secret = os.getenv('LASTFM_SHARED_SECRET')
        if api_key is not None and shared_secret is not None:
            creds['last_fm'] = {
                'api_key': api_key,
                'shared_secret': shared_secret
            }
            return creds
    except Exception as e:
        print(f"Failed to get credentials from keyring or .env: {e}")
        return None

def has_credentials() -> bool:
    """Determines if credentials exist (in either the system
    keyring or local .env)"""
    # check keyring
    keyring_creds = get_credentials()
    if keyring_creds and (keyring_creds['last_fm']['api_key'] is not None)\
        and (keyring_creds['last_fm']['shared_secret'] is not None):
            return True
    
    # check .env
    try:
        api_key = os.getenv('LASTFM_API_KEY')
        shared_secret = os.getenv('LASTFM_SHARED_SECRET')
        return api_key is not None and shared_secret is not None
    except Exception as e:
        return False
    
def delete_credentials() -> bool:
    """Deletes credentials from keyring"""
    try:
        # last_fm
        kr.delete_password(SERVICE_NAME, 'last_fm-api_key')
        kr.delete_password(SERVICE_NAME, 'last_fm-shared_secret')
        return True
    except Exception as e:
        print(f"Failed to delete credentials from keyring: {e}")
        return False
    
def move_env_to_keyring() -> bool:
    """Copies the .env credentials over to the keyring"""
    # setup
    creds = {'last_fm': {}}
    
    try:
        # grab from .env
        api_key = os.getenv('LASTFM_API_KEY')
        shared_secret = os.getenv('LASTFM_SHARED_SECRET')
        if api_key is not None and shared_secret is not None:
            creds['last_fm'] = {
                'api_key': api_key,
                'shared_secret': shared_secret
            }
            return save_credentials(creds)
        return False
    except Exception as e:
        print(f"Failed to move .env credentials to keyring: {e}")
        return False