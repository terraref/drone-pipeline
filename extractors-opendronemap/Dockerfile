#FROM clowder/extractors-opendronemap
FROM chrisatua/extractors:opendronemap

LABEL maintainer="Chris Schnaufer <chris.schnaufer@email.arizona.edu>"

# Install any users
RUN useradd -u 49044 extractor \
    && mkdir /home/extractor \
    && mkdir /home/extractor/sites

RUN chown -R extractor /home/extractor \
    && chgrp -R extractor /home/extractor 

RUN pip install -U pip && \
    pip install -U numpy && \
    pip install -U pyclowder && \
    pip install -U utm influxdb laspy piexif && \
    pip install --ignore-installed enum34 terrautils

# Copy our source files
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
    RABBITMQ_QUEUE="terra.dronepipeline.opendronemap" \
    MAIN_SCRIPT="terraref-opendronemap.py" \
    PYTHONPATH="${PYTHONPATH}:/code"
