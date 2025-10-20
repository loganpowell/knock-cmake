#!/bin/bash

# uPDFParser
if [ ! -d lib/updfparser ] ; then
    git clone git://soutade.fr/soutade/updfparser.git lib/updfparser
    pushd lib/updfparser
    make BUILD_STATIC=1 BUILD_SHARED=0
    popd
fi
