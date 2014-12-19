#!/usr/bin/python2.7
from oslo.config import cfg
from neutron.agent.common import config as agent_config
from neutron.agent.linux import daemon
from neutron.agent.linux import ip_lib
from neutron.agent.linux import utils as agent_utils
from neutron.common import config
from neutron.common import utils
from neutron.openstack.common import log as logging
import time


LOG = logging.getLogger(__name__)


EBTABLES_TEMPLATE = (
    """# Generated for ebtables-save v1.0
*filter
:INPUT ACCEPT
:FORWARD ACCEPT
:OUTPUT ACCEPT

*nat
:PREROUTING ACCEPT
:OUTPUT ACCEPT
:POSTROUTING ACCEPT
""")

PREROUTING_DNAT = ("-A PREROUTING -p IPv4 -d %(ovh_vmac)s --ip-dst %(ip)s -j dnat "
                   "--to-dst %(mac)s --dnat-target ACCEPT\n"
                   "-A PREROUTING -p ARP --arp-ip-dst %(ip)s -j dnat "
                   "--to-dst %(mac)s --dnat-target ACCEPT\n")

FINAL_POSTROUTING = ("-A POSTROUTING -s %(mac)s -j snat "
                     "--to-src %(ovh_vmac)s --snat-arp --snat-target ACCEPT\n")


class OvhEbtablesDaemon(daemon.Daemon):

    def __init__(self, pid_file, root_helper, update_interval, ovh_vmac,
                 openstack_vmacs):
        self.root_helper = root_helper
        self.update_interval = update_interval
        self.ovh_vmac = ovh_vmac
        self.openstack_vmacs = openstack_vmacs
        self.current_ebtables = None
        super(OvhEbtablesDaemon, self).__init__(pid_file)

    def _start(self):
        self.current_ebtables = self.gen_ebtables()
        self._ebtables_restore(current_ebtables)

    def _build_ebtables(self, pairs):
        """Build in the ebtables-save format, change this to jinja template"""
        table = EBTABLES_TEMPLATE
        d = {'ovh_vmac': self.ovh_vmac,
             'os_vmacs': self.openstack_vmacs}
        for mac, addrs in pairs.items():
            d['mac'] = mac
            for addr in addrs:
                if addr['ip_version'] == 4:
                    d['ip'] = addr['cidr'].split("/")[0]
                    table += PREROUTING_DNAT % d

        for mac in pairs.keys():
            d['mac'] = mac
            table += FINAL_POSTROUTING % d

        return table

    def _get_qrouter_namespaces(self):
        root_ip = ip_lib.IPWrapper()
        host_namespaces = root_ip.get_namespaces(None)
        return (ns for ns in host_namespaces if ns.startswith("qrouter-"))

    def _get_mac_addr_pairs(self, namespaces):
        pairs = {}
        for ns in namespaces:
            ns_ip = ip_lib.IPWrapper(self.root_helper, namespace=ns)
            for dev in ns_ip.get_devices(exclude_loopback=True):
                if dev.name.startswith("qg-"):
                    pairs[dev.link.address] = dev.addr.list()
        return pairs

    def _ebtables_restore(self, tables):
        agent_utils.execute(['ebtables-restore'],
                            process_input=tables,
                            root_helper=self.root_helper)

    def _gen_ebtables(self):
        namespaces = self._get_qrouter_namespaces()
        pairs = self._get_mac_addr_pairs(namespaces)
        return self._build_ebtables(pairs)

    def run(self):
        while True:
            new_ebtables = self._gen_ebtables()
            if new_ebtables != self.current_ebtables:
                self._ebtables_restore(new_ebtables)
                self.current_ebtables = new_ebtables
            time.sleep(self.update_interval)


def main():
    opts = [
        cfg.StrOpt('pid_file',
                   help=_('Location of pid file of this process.')),
        cfg.BoolOpt('daemonize',
                    default=True,
                    help=_('Run as daemon.'))
    ]

    config_opts = [
        cfg.StrOpt('ovh_vmac',
                   help=_('OVH vMAC where all floating IPs are '
                          'assigned to.')),
        cfg.StrOpt('openstack_vmacs',
                   help=_('Openstack vMAC ranges'),
                   default='fa:16:3e:0:0:0/ff:ff:ff:0:0:0'),
        cfg.IntOpt('update_interval',
                   help=_('router poll and ebtables update interval'
                          'in seconds'),
                   default=5)
        ]

    cfg.CONF.register_opts(config_opts)
    cfg.CONF.register_cli_opts(opts)
    agent_config.register_root_helper(cfg.CONF)
    # Don't get the default configuration file
    cfg.CONF(project='neutron', default_config_files=[])
    config.setup_logging()
    utils.log_opt_values(LOG)
    ovh_daemon = OvhEbtablesDaemon(cfg.CONF.pid_file,
                                   agent_config.get_root_helper(cfg.CONF),
                                   cfg.CONF.update_interval,
                                   cfg.CONF.ovh_vmac,
                                   cfg.CONF.openstack_vmacs)

    if cfg.CONF.daemonize:
        ovh_daemon.start()
    else:
        ovh_daemon.run()

if __name__ == "__main__":
    main()
