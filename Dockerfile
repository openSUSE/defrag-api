# build it with:
#   podman build -t <image name> .
# run it with:
#   podman run -d --name <container name> -p 8000:8000 --env-file ./.env <image name>
#       (remove `--env-file <path>` if you are not using any environment var file)
# clean it up with:
#   podman container prune
#   podman image prune -a

FROM tiangolo/uvicorn-gunicorn-fastapi:python3.8
EXPOSE 8000
COPY ./requirements.txt ./.env /opt/app/
ADD ./defrag /opt/app/defrag/
WORKDIR /opt/app
CMD pip install -r requirements.txt
CMD python -m defrag