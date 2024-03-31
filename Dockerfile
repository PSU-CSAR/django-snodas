FROM postgis/postgis:16-3.4

RUN set -x && \
    apt-get update && \
    apt-get install -y curl make && \
    mkdir /tmp/pg_tms && \
    cd /tmp/pg_tms && \
    curl -sLo ./pg_tms.tar.gz \
        https://github.com/jkeifer/pg_tms/archive/refs/tags/v0.0.4.tar.gz && \
    tar -xzf pg_tms.tar.gz && \
    cd pg_tms-0.0.4 && \
    make install && \
    apt-get remove -y curl make && \
    apt-get clean -y && \
    rm -r /var/lib/apt/lists/*
