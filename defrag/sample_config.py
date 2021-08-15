if __name__.endswith("sample_config"):
    import sys
    print("The README is there to be read. Extend this sample config to a config file "
        "and rename it to 'config.py'. Quiting.", file=sys.stderr)
    sys.exit(1)

# Configuration file for defrag.

class Config:    
    # Redis configuration
    REDIS_HOST = localhost # Host the Redis server runs at
    REDIS_PORT = 16052 # Port for the Redis server
    REDIS_PWD = "password" # Password for the Redis server, blank if none

    # Bugzilla configuration
    BUGZILLA_USER = "username" # Your openSUSE infrastructure username
    BUGZILLA_PASSWORD = "password" # Your openSUSE infrastructure password

    # Module configuration
    NO_LOAD = [] # List of modules that should not be loaded
