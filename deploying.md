# Deploying
There are multiple ways of deploying the defrag API.
## Using Podman
Using Podman is probably the easiest method.

### Using prebuilt containers
1. Create a .env file as described in [configuration.md](configuration.md).
2. Make sure you have Podman installed: `sudo zypper install podman`
3. Run the container: `podman run --env-file /path/to/env/file -p 8080:8000 registry.opensuse.org/opensuse/infrastructure/defrag/containers/containers/defrag:latest`. Replace the `/path/to/env/file` with the actual path tp your env file.
4. The API should be reachable at [http://localhost:8080](http://localhost:8080).

### Building the container yourself
1. Clone this repository and navigate into it.
2. Make sure you have Podman installed: `sudo zypper install podman`
3. Build the container: `sudo podman build . -t defrag`
4. Create a .env file as described in [configuration.md](configuration.md).
5. Run the container: `podman run --env-file /path/to/env/file -p 8080:8000 defrag`. Replace the `/path/to/env/file` with the actual path tp your env file.

## By using prebuilt packages
On an openSUSE Tumbleweed machine, you can install defrag from the Open Build Service.

1. Open a root shell with `sudo -s`
2. Add the repository using `zypper addrepo https://download.opensuse.org/repositories/openSUSE:infrastructure:defrag/openSUSE_Tumbleweed/ defrag`
3. Update the zypper cache: `zypper refresh`
4. Install the package: `zypper install python38-defrag-api`
5. Exit the root shell: `exit`
6. You can now run the API using `python3.8 -m defrag`. Please check [configuration.md](configuration.md) first however!

## By using git
This is the advised method if you want to work on the API.

1. Clone this repository and navigate into it.
2. Create a virtual environment: `python3 -m venv venv`
3. Activate the venv: `. venv/bin/activate`
4. Install the required dependencies: `pip install -r requirements.txt`
5. Configure everything following [configuration.md](configuration.md).
6. Run the API by using `python3 -m defrag`.
