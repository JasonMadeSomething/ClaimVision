import os

def get_database_url():
    """
    Construct the database URL from environment variables.
    
    Returns
    -------
    str
        The database URL.
    """
    username = os.getenv("DB_USERNAME")
    password = os.getenv("DB_PASSWORD")
    host = os.getenv("DB_HOST")
    name = os.getenv("DB_NAME", "claimvision")
    
    return f"postgresql://{username}:{password}@{host}:5432/{name}"
