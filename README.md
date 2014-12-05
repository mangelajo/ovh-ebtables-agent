ovh-ebtables-agent
==================

Neutron OVH ebtables agent to make neutron external connectivity compatible with OVH network.

Problem 1
---------
OVH (soyoustart, kimsufi, ovh) has a peculiar network when it comes to floating IP addresses,
you can assign /32 to /28 RIPE ip blocks to your machine, and setup the MACs of those
IP addresses individually via their API or control panel. This is the first conflict point
with neutron, where as it will chose a random MAC address for every new external interface
on routers (you can create an external one with an specific MAC address).

This is what we address with this agent, and the deployment described on problem 2.

We use ebtables to manipulate MAC addresses on ingoing and outgoing traffic over br0
to make all packets seem coming from the same vMAC address, and translating any
traffic comming back to the neutron expected MAC address.

The information is got from inspecting the qrouter-* namespaces on the host, which
is faster compared to querying ports, agent associations, etc, via API. But it's
implementation dependent.

This is an example of ebtables configured by the agent::

    # ebtables-save
    # Generated by ebtables-save v1.0 on vie dic  5 17:16:53 CET 2014
    *filter
    :INPUT ACCEPT
    :FORWARD ACCEPT
    :OUTPUT ACCEPT
  
    *nat
    :PREROUTING ACCEPT
    :OUTPUT ACCEPT
    :POSTROUTING ACCEPT
    -A PREROUTING -p IPv4 --ip-dst 5.196.247.72 -j dnat --to-dst fa:16:3e:9e:ec:85 --dnat-target ACCEPT
    -A PREROUTING -p ARP --arp-ip-dst 5.196.247.72 -j dnat --to-dst fa:16:3e:9e:ec:85 --dnat-target ACCEPT
    -A PREROUTING -p IPv4 --ip-dst 5.196.247.73 -j dnat --to-dst fa:16:3e:9e:ec:85 --dnat-target ACCEPT
    -A PREROUTING -p ARP --arp-ip-dst 5.196.247.73 -j dnat --to-dst fa:16:3e:9e:ec:85 --dnat-target ACCEPT
    -A PREROUTING -p IPv4 --ip-dst 5.196.247.74 -j dnat --to-dst fa:16:3e:9e:ec:85 --dnat-target ACCEPT
    -A PREROUTING -p ARP --arp-ip-dst 5.196.247.74 -j dnat --to-dst fa:16:3e:9e:ec:85 --dnat-target ACCEPT
    -A POSTROUTING -s fa:16:3e:9e:ec:85 -j snat --to-src 2:0:0:9f:4e:6f --snat-arp --snat-target ACCEPT 


Ebtables does the work, but I eventually want to experiment with openvswitch + openflow for 
performance reasons.

Problem 2
---------
We have a single NIC, and we need to setup tenant networks and controller traffic
all over the same NIC.

To overcome this problem, we provide an script to rearrange your network as

from::

    eth0[IP]

to::

    eth0 -- br0[IP]
             <---veth-br  . . .  veth-neutron --> br-external

Problem 3
---------
It also has another peculiarity, the gateway for those IP addresses is outside of it's
own subnet (so you can use the full block instead of saving one for the router, one
for broadcast). This case is yet not well suported in the neutron-l3-agent, that needs
to setup an onlink route to the gateway before the default route through the gateway.

This is handled by a patch to the l3 agent.



