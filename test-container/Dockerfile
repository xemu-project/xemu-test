FROM ubuntu:20.04
RUN apt-get update \
 && DEBIAN_FRONTEND=noninteractive \
    apt-get install -qy \
        build-essential cmake git python3-pip
RUN git clone --depth=1 https://github.com/mborgerson/fatx \
 && cd fatx \
 && mkdir -p /whl \
 && python3 -m pip wheel -w /whl .

FROM ubuntu:20.04
RUN set -xe; \
    apt-get -qy update \
    && DEBIAN_FRONTEND=noninteractive \
    apt-get -qy install \
        python3-pip \
        xvfb \
        x11-utils \
        x11vnc \
        xinit \
        ffmpeg \
        i3 \
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

COPY --from=0 /whl /whl
RUN python3 -m pip install --find-links /whl /whl/pyfatx-*.whl

ENV SDL_AUDIODRIVER=disk
ENV SDL_DISKAUDIOFILE=/dev/null
EXPOSE 5900

COPY ./docker_entry.sh /usr/local/bin/docker_entry.sh
ENTRYPOINT ["/usr/local/bin/docker_entry.sh"]
