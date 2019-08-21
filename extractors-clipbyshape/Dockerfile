FROM terraref/terrautils:1.4
MAINTAINER Chris Schnaufer <schnaufer@email.arizona.edu>

# Install any users
RUN useradd -u 49044 extractor \
    && mkdir /home/extractor \
    && mkdir /home/extractor/sites

RUN chown -R extractor /home/extractor \
    && chgrp -R extractor /home/extractor 

# install and upgrade packages
RUN apt install -y imagemagick gdal-bin libgdal-dev

RUN pip install --upgrade pip 

RUN pip install -U numpy && \
    pip install -U dbfread && \
    pip install gdal  && \
    pip install --upgrade --ignore-installed enum34 terrautils

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
