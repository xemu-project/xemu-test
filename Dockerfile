FROM xboxdev/nxdk:latest AS nxdk-base


#
# Build test data
#
FROM nxdk-base AS test-xbe-data
RUN mkdir /data

COPY test-xbe /test-xbe
RUN mkdir /data/TestXBE
RUN /usr/src/nxdk/docker_entry.sh make -C /test-xbe
RUN cp /test-xbe/tester.iso /data/TestXBE/


#
# Build nxdk_pgraph_tests
#
FROM nxdk-base AS pgraph-data

RUN apk add --upgrade --no-cache curl libcurl git

WORKDIR /work

RUN mkdir -p /data/TestNxdkPgraphTests
RUN curl \
    -L https://github.com/abaire/nxdk_pgraph_tests/releases/download/v2026-01-23_17-51-44-155274729/nxdk_pgraph_tests_xiso.iso \
    --output /data/TestNxdkPgraphTests/nxdk_pgraph_tests_xiso.iso
RUN git clone --depth 1 https://github.com/abaire/nxdk_pgraph_tests_golden_results.git /data/TestNxdkPgraphTests/nxdk_pgraph_tests_golden_results

FROM ubuntu:25.10 AS ubuntu-base
RUN set -xe; \
    apt-get -qy update \
    && apt-get -qy install \
        python3-pip \
        python3-venv \
    ;

#
# Build xemutest module
#
FROM ubuntu-base AS build-xemutest

RUN apt-get -qy install \
        cmake \
        ;

WORKDIR /build
COPY . /work/xemu-test
RUN python3 -m venv venv \
    && . venv/bin/activate \
    && pip install /work/xemu-test \
    ;


#
# Build base test container image
#
FROM ubuntu-base AS run-container-base
ENV DEBIAN_FRONTEND=noninteractive
RUN apt-get -qy install \
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
        libssl-dev \
        libstdc++6 \
        perceptualdiff \
        zlib1g \
        ;

# Combine test data
FROM scratch AS data
COPY --from=test-xbe-data /data /data
COPY --from=pgraph-data /data/TestNxdkPgraphTests /data/TestNxdkPgraphTests

#
# Build final test container
#
FROM run-container-base AS test-container
ENV DEBIAN_FRONTEND=noninteractive
ENV SDL_AUDIODRIVER=dummy

# VNC port for debugging

EXPOSE 5900

WORKDIR /work

COPY scripts/docker_entry.sh /docker_entry.sh
COPY ./scripts /work/xemu-test/scripts/
COPY --from=data /data /work/xemu-test/data
COPY --from=build-xemutest /build/venv /venv

ENTRYPOINT ["/docker_entry.sh"]

CMD ["/venv/bin/python3", "-m", "xemutest", "--data", "/work/xemu-test/data", "xemu", "/work/private", "/work/results"]
