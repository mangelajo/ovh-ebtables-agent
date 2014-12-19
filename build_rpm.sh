#!/bin/sh
set -e
set -x
# download the sources package
spectool -g -R ovh-ebtables-agent.spec

# build srpm and rpm
rpmbuild -ba ovh-ebtables-agent.spec
