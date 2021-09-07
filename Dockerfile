# for some reason I have build with `podman build --cgroup-manager cgroupfs`
FROM tiangolo/uvicorn-gunicorn-fastapi:python3.8
RUN pip install --no-cache-dir pipenv
WORKDIR /app
COPY ./.env requirements.txt ./
COPY ./defrag ./defrag
RUN pipenv install -r requirements.txt
EXPOSE 8000
# runs the application on maximum of 4 uvicorn workers
# (remove the first two elements from the list below to run without pipenv)
CMD ["pipenv", "run", "gunicorn", "-w", "4" , "-k", "uvicorn.workers.UvicornWorker", "defrag.main:app"]
