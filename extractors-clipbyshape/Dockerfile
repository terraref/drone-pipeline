FROM terraref/terrautils:python3
LABEL maintainer="Chris Schnaufer <schnaufer@email.arizona.edu>"

# Install any users
RUN useradd -u 49044 extractor \
    && mkdir /home/extractor \
    && mkdir /home/extractor/sites

RUN chown -R extractor /home/extractor \
    && chgrp -R extractor /home/extractor 

# install and upgrade packages
RUN apt-get update && \
    apt-get install -y imagemagick \
        gdal-bin \
        libgdal-dev \
        python3-gdal \
        python3-pip && \
    python3 -m pip install -U \
        pip \
        numpy \
        dbfread \
        utm \
        influxdb \
        laspy \
        python-dateutil \
        pyclowder && \
    python3 -m pip install -U cryptography && \
    python3 -m pip install gdal
RUN    python3 -m pip install --upgrade terrautils

RUN apt-get autoremove -y && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# command to run when starting docker
COPY entrypoint.sh extractor_info.json *.py /home/extractor/

USER extractor
ENTRYPOINT ["/home/extractor/entrypoint.sh"]
CMD ["extractor"]

# Setup environment variables. These are passed into the container. You can change
# these to your setup. If RABBITMQ_URI is not set, it will try and use the rabbitmq
# server that is linked into the container. MAIN_SCRIPT is set to the script to be
# executed by entrypoint.sh
ENV RABBITMQ_EXCHANGE="terra" \
    RABBITMQ_VHOST="%2F" \
    RABBITMQ_QUEUE="terra.dronepipeline.clipbyshape" \
    MAIN_SCRIPT="terra_clipbyshape.py"
