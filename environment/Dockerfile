# hash:sha256:237a603805bbf1fecd5c84e8443c9fa1b7da9bec62c0a016731fd78113ec8904
ARG REGISTRY_HOST
FROM $REGISTRY_HOST/codeocean/mambaforge3:23.1.0-4-python3.10.12-ubuntu22.04

ARG DEBIAN_FRONTEND=noninteractive

ARG GIT_ASKPASS
ARG GIT_ACCESS_TOKEN
COPY git-askpass /

RUN pip install -U --no-cache-dir \
    aind-data-schema==1.2.0 \
    aind-data-schema-models==0.6.1 \
    aind-qcportal-schema==0.1.1 \
    pillow==10.4.0 \
    pydantic==2.8.1
