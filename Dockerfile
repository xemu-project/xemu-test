#
# Build test data
#
FROM ghcr.io/xboxdev/nxdk AS test-xbe-data
RUN mkdir /data

COPY test-xbe /test-xbe
RUN mkdir /data/TestXBE
RUN /usr/src/nxdk/docker_entry.sh make -C /test-xbe
RUN cp /test-xbe/tester.iso /data/TestXBE/

# The nxdk_pgraph_tests includes its own copy of the nxdk which needs more build
# infrastructure than the nxdk-runbase used for other tests.
FROM ubuntu:20.04 AS pgraph-buildbase
ENV DEBIAN_FRONTEND noninteractive
RUN set -xe; \
    apt-get -qy update \
    && apt-get -qy install \
        bison \
        clang \
        cmake \
        flex \
        lld \
        llvm \
        make

FROM pgraph-buildbase AS pgraph-data
RUN mkdir -p /data/TestNXDKPgraphTests
COPY test-pgraph /test-pgraph
RUN make -C /test-pgraph/nxdk_pgraph_tests \
    AUTORUN_IMMEDIATELY=y \
    ENABLE_SHUTDOWN=y \
    ENABLE_PROGRESS_LOG=y \
    FALLBACK_OUTPUT_ROOT_PATH="c:" \
    RUNTIME_CONFIG_PATH="c:/pgraph_tests.cnf" \
    CC=clang CXX=clang++ \
    -j$(numproc)
RUN cp /test-pgraph/nxdk_pgraph_tests/nxdk_pgraph_tests.iso /data/TestNXDKPgraphTests/
RUN mv /test-pgraph/config.cnf /data/TestNXDKPgraphTests/
RUN mv /test-pgraph/golden_results /data/TestNXDKPgraphTests/

# Combine test data
FROM scratch AS data
COPY --from=test-xbe-data /data /data
COPY --from=pgraph-data /data/TestNXDKPgraphTests /data/TestNXDKPgraphTests

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
        perceptualdiff \
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
COPY ./scripts /work/xemu-test/scripts/
COPY ./xemutest /work/xemu-test/xemutest/
COPY ./setup.py /work/xemu-test
COPY --from=data /data /work/xemu-test/xemutest/data
RUN pip install /work/xemu-test
ENTRYPOINT ["/docker_entry.sh"]
CMD ["/usr/bin/python3", "-m", "xemutest", "/work/private", "/work/results"]
