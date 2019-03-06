#FROM clowder/extractors-opendronemap
FROM chrisatua/extractors:opendronemap

MAINTAINER Chris Schnaufer <chris.schnaufer@email.arizona.edu>

# Install any users and programs needed
RUN useradd -u 49044 extractor \
    && mkdir /home/extractor \
    && chown -R extractor /home/extractor

RUN curl --get https://raw.githubusercontent.com/GitHubRGI/geopackage-python/master/Tiling/gdal2tiles_parallel.py > gdal2tiles_parallel.py  && \
    mv gdal2tiles_parallel.py /home/extractor/gdal2tiles_parallel.py

RUN pip install --upgrade pip && \
    pip install -U numpy && \
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
