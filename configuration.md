# Configuration
You can configure the software using two different ways: Using a configuration file or
environment variables. 

## Config keys
Both the configuration file and the environment variables share the same keys, listed below.

|name	|type	|description	|required	|
 --- | --- | --- | ---
|REDIS_HOST	|String	|Host the Redis server runs at	|yes	|
|REDIS_PORT	|Int	|Port for the Redis server	|yes	|
|REDIS_PWD	|String	|Password for the Redis server, blank if none	|no	|
|BUGZILLA_USER	|String	|Your openSUSE infrastructure username|yes	|
|BUGZILLA_PASSWORD	|String	|Your openSUSE infrastructure password	|yes|
|NO_LOAD	|String	|List of modules that should not be loaded. See below for details.	|yes, but can be empty|
|TWITTER_CONSUMER_KEY	|String				||yes	|
|TWITTER_CONSUMER_SECRET|String				||yes	|
|TWITTER_ACCESS_TOKEN	|String 			||yes	|
|TWITTER_ACCESS_TOKEN_SECRET	|String			||yes 	|

## File based configuration
Copy the file `config_sample.ini` to `config.ini`. It looks like this:

```ini
# Defrag sample configuration file
# Copy to config.ini and replace the values!

[REDIS]
# Host the Redis server runs at
REDIS_HOST = localhost

# Port for the Redis server
REDIS_PORT = 16052

# Password for the Redis server, blank if none
REDIS_PWD = password

[BUGZILLA]
# Your openSUSE infrastructure username
BUGZILLA_USER = username

# Your openSUSE infrastructure password
BUGZILLA_PASSWORD = password

[MODULES]
# List of modules that should not be loaded
# e.g. NO_LOAD = ["bugs", "twitter"]
NO_LOAD = []

[TWITTER]
# Obtain from Twitter developer portal
TWITTER_CONSUMER_KEY =
TWITTER_CONSUMER_SECRET =
TWITTER_ACCESS_TOKEN =
TWITTER_ACCESS_TOKEN_SECRET = 
```

## Env based configuration
If you want to use environemt based configuration, create a `.env` file in the root of the project and fill in the values.
Setting the variables is pretty simple, it's just a `key=value` principle.
However, the `NO_LOAD` variable is special, as it is a list. So, if you want to block multiple
modules from loading, seperate them by spaces:
`NO_LOAD="bugs reddit"`.
