version=3

opts=filenamemangle=s/.+\/v?(\d\S*)\.tar\.gz/splitcpy-$1\.tar\.gz/ \
 https://github.com/davesteele/splitcpy/tags upstream/(.*)\.tar\.gz
