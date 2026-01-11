#!/bin/bash
if [[ ! -d xemutest ]]; then
	echo "Run from root dir"
	exit 1
fi

set -ex
target=data
image=xemu-test-data-tmp-img
docker build --target $target -t $image .
container=$(docker create $image "")
docker cp $container:/data xemutest/
docker rm $container
docker rmi -f $image
