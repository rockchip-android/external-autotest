# Copyright (c) 2014 The Chromium OS Authors. All rights reserved.
# Use of this source code is governed by a BSD-style license that can be
# found in the LICENSE file.


import re
import logging

import common
import requests
from autotest_lib.site_utils.stats import registry
from autotest_lib.site_utils.graphite import stats


# requests will log at INFO and DEBUG, which gets automatically enabled by
# default by autotest code.  Let's silence these.
requests_logger = logging.getLogger('requests.packages.urllib3.connectionpool')
requests_logger.setLevel(logging.WARNING)


@registry.loop_stat('sam')
def rpcs_per_sec(server):
    """
    Scrape the requests/sec number off of the apache server-status page and
    submit it as a stat to statsd.

    @param server: The AFE server.
    """
    try:
        page = requests.get('http://%s/server-status' % server).text
    except requests.ConnectionError as e:
        logging.exception(e)
        return

    m = re.search("(\d+) requests/sec", page)
    if m:
        val = int(m.groups(0)[0])
        stat = stats.Gauge(server, bare=True)
        stat.send('requests_per_sec', val)
