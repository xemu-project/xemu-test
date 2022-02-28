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
# Build pyfatx for HDD management
#
FROM ubuntu:20.04 AS pyfatx
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
 && apt-get install -qy \
     build-essential \
     cmake \
     git \
     python3-pip
RUN git clone --depth=1 https://github.com/mborgerson/fatx \
 && mkdir -p /whl \
 && python3 -m pip wheel -w /whl ./fatx

#
# Build test ISO
#
FROM ghcr.io/xboxdev/nxdk AS test-iso-1
COPY test-xbe /test-xbe
RUN /usr/src/nxdk/docker_entry.sh make -C /test-xbe

#
# Build final test container
#
FROM run-container-base

RUN useradd -ms /bin/bash user

COPY --from=pyfatx /whl /whl
RUN python3 -m pip install --find-links /whl /whl/pyfatx-*.whl

ENV DEBIAN_FRONTEND=noninteractive
ENV SDL_AUDIODRIVER=dummy

# VNC port for debugging
EXPOSE 5900

COPY docker_entry.sh /docker_entry.sh
ENTRYPOINT ["/docker_entry.sh"]

RUN mkdir /work
COPY test.py /work/test.py
COPY xbox_hdd.qcow2 /work/xbox_hdd.qcow2
COPY --from=test-iso-1 /test-xbe/tester.iso /work/tester.iso

WORKDIR /work
CMD ["/usr/bin/python3", "/work/test.py"]
