#!/usr/bin/env python
'''views.py: Split Horizon rewriter plugin for the Unbound DNS resolver'''

# Copyright © 2012-2019, Yarema <yds@Necessitu.de>
#
# This software is open source.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions
# are met:
#
#    * Redistributions of source code must retain the above copyright notice,
#      this list of conditions and the following disclaimer.
#
#    * Redistributions in binary form must reproduce the above copyright notice,
#      this list of conditions and the following disclaimer in the documentation
#      and/or other materials provided with the distribution.
#
#    * Neither the name of the organization nor the names of its
#      contributors may be used to endorse or promote products derived from this
#      software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
# "AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED
# TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR
# PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE REGENTS OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

import os
import yaml
from socket import inet_aton
from netaddr import *

views = {}	# The Split Horizon dictionary

def init(id, cfg):
    '''Populate the external to internal address mapping'''
    addrs = {}	# IPv4 address(es) on internal (LAN) interface
    config = yaml.load(open(os.path.splitext(cfg.python_script)[0]+'.yml'))
    for ifs in config.keys():
        if type(config[ifs]) is dict:
            for ip in [l.split()[1] for l in os.popen('/sbin/ifconfig %s 2>/dev/null' % ifs) if l.split()[0] == 'inet']:
                addrs[ip] = IPAddress(ip)   # Collect IPv4 addresses configured on ifs
            for wan, lan in config[ifs].items():
                wan = IPNetwork(wan)
                lan = IPNetwork(lan)
                for ip in addrs:
                    if addrs[ip] in lan:
                        # Key the views with a four byte binary of the external IPv4 address
                        views.update(zip(map(inet_aton, map(str, wan)), map(str, lan)))
    return True

def deinit(id):
    return True

def inform_super(id, qstate, superqstate, qdata):
    return True

def operate(id, event, qstate, qdata):
    '''Rewrite to internal address if iterator fetches an external address'''

    if event == MODULE_EVENT_NEW or event == MODULE_EVENT_PASS:
        # Pass on the new event to the iterator
        qstate.ext_state[id] = MODULE_WAIT_MODULE
        return True

    if event == MODULE_EVENT_MODDONE:
        # Iterator finished, show response (if any)
        if qstate.return_msg:
            r = qstate.return_msg.rep
            if r:
                for i in range(0, r.rrset_count):
                    rr = r.rrsets[i]
                    if rr.rk.type_str == 'A':
                        d = rr.entry.data
                        for j in range(0, d.count+d.rrsig_count):
                            addr = d.rr_data[j][2:6]	# The last four bytes contain the IPv4 address
                            if addr in views:
                                msg = DNSMessage(qstate.qinfo.qname_str, RR_TYPE_A, RR_CLASS_IN, PKT_QR | PKT_RA | PKT_AA)
                                msg.answer.append('%s IN A %s' % (qstate.qinfo.qname_str, views[addr]))
                                if msg.set_return_msg(qstate):
                                    qstate.return_msg.rep.security = 2	# we don't need validation, result is valid
                                    qstate.return_rcode = RCODE_NOERROR
                                else:
                                    log_err("pythonmod: cannot create response")
                                    qstate.ext_state[id] = MODULE_ERROR
                                    return True
        qstate.ext_state[id] = MODULE_FINISHED
        return True

    log_err("pythonmod: bad event")
    qstate.ext_state[id] = MODULE_ERROR
    return True

if __name__ == '__main__':
    config = yaml.load(open(os.path.splitext(__file__)[0]+'.yml'))
    if 'redirect' in config:
        redirect = config['redirect']
        del config['redirect']
    else:
        redirect = 'rdr on wan0 proto tcp to {wan} -> {lan}'
    for ifs in config.keys():
        for wan, lan in config[ifs].items():
            wan = IPNetwork(wan)
            lan = IPNetwork(lan)
            views.update(zip(map(str, wan), map(str, lan)))
    for wan in sorted(views, key=inet_aton):
        print(redirect.format(wan=wan, lan=views[wan]))
