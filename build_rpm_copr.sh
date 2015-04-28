#!/bin/sh
set -e
set -x
# download the sources package
spectool -g -R ovh-ebtables-agent.spec 2>&1 >/dev/null

# build srpm and rpm
rpmbuild --quiet -bs ovh-ebtables-agent.spec
