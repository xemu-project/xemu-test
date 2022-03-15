#
# Build test data
#
FROM ghcr.io/xboxdev/nxdk AS data
RUN mkdir /data

COPY test-xbe /test-xbe
RUN mkdir /data/TestXBE
RUN /usr/src/nxdk/docker_entry.sh make -C /test-xbe
RUN cp /test-xbe/tester.iso /data/TestXBE/

#
# Build base test container image
#
FROM ubuntu:20.04 as run-container-base
ENV DEBIAN_FRONTEND=noninteractive
RUN set -xe; \
    apt-get -qy update \
    && apt-get -qy install \
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
        ;

#
# Build final test container
#
FROM run-container-base AS test-container
ENV DEBIAN_FRONTEND=noninteractive
ENV SDL_AUDIODRIVER=dummy

# VNC port for debugging
EXPOSE 5900

RUN mkdir /work
WORKDIR /work
COPY scripts/docker_entry.sh /docker_entry.sh
COPY . /work/xemu-test
COPY --from=data /data /work/xemu-test/xemutest/data
RUN pip install /work/xemu-test
ENTRYPOINT ["/docker_entry.sh"]
CMD ["/usr/bin/python3", "-m", "xemutest", "/work/private", "/work/results"]
