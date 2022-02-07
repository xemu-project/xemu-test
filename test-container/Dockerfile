FROM ubuntu:20.04
RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive apt-get install -qy fuse build-essential pkg-config libfuse-dev cmake git
RUN mkdir -p /usr/src \
 && git clone https://github.com/mborgerson/fatx.git /usr/src/fatx
WORKDIR /usr/src/fatx
RUN mkdir build \
 && cd build \
 && cmake .. \
 && make DESTDIR=/fatx install

FROM ubuntu:20.04
RUN set -xe; \
    apt-get -qy update \
    && DEBIAN_FRONTEND=noninteractive \
    apt-get -qy install \
        xvfb \
        x11-utils \
        x11vnc \
        xinit \
        ffmpeg \
        i3 \
        fuse \
        qemu-utils \
        libc6 \
        libepoxy0 \
        libgcc-s1 \
        libglib2.0-0 \
        libgtk-3-0 \
        libpcap0.8 \
        libpixman-1-0 \
        libpulse0 \
        libsamplerate0 \
        libsdl2-2.0-0 \
        libssl1.1 \
        libstdc++6 \
        zlib1g \
        cpu-checker \
        ;

COPY --from=0 /fatx /fatx
RUN cp -ruT /fatx / && rm -rf /fatx

ENV SDL_AUDIODRIVER=disk
ENV SDL_DISKAUDIOFILE=/dev/null
EXPOSE 5900

COPY ./docker_entry.sh /usr/local/bin/docker_entry.sh
ENTRYPOINT ["/usr/local/bin/docker_entry.sh"]
