FROM public.ecr.aws/docker/library/r-base:4.1.2 as base

# Install tidyverse
RUN apt update && apt-get install -y --no-install-recommends \
    r-cran-tidyverse

RUN R -e "install.packages(c('rjson'))"


### start of PROCESSING container
FROM base as processing
ENTRYPOINT ["Rscript"]

### start of TRAINING container
FROM base as training
RUN apt-get -y update && apt-get install -y --no-install-recommends \
    wget \
    apt-transport-https \
    ca-certificates \
    libcurl4-openssl-dev \
    libsodium-dev

RUN apt-get update && apt-get install -y python3-dev python3-pip python3-boto3
#RUN pip3 install boto3
RUN R -e "install.packages('reticulate',dependencies=TRUE, repos='http://cran.rstudio.com/')"
RUN R -e "install.packages(c('readr','plumber'))"

ENV PATH="/opt/ml/code:${PATH}"

WORKDIR /opt/ml/code

COPY docker_helpers/run.sh /opt/ml/code/run.sh
COPY docker_helpers/entrypoint.R /opt/ml/entrypoint.R

RUN /bin/bash -c 'chmod +x /opt/ml/code/run.sh'

ENTRYPOINT ["/bin/bash", "run.sh"]
