# [Unbound-Views][]

[Unbound-Views][] is a Split-Horizon Views plugin for the [Unbound][] DNS resolver.

## Problem: [Redirection and Reflection][Reflection]

Quoting from the [OpenBSD pf FAQ][Reflection]:

> Often, redirection rules are used to forward incoming connections from the Internet to a local server with a private address in the internal network or LAN, as in:
>
>     server = 192.168.1.40
>
>     pass in on $ext_if proto tcp from any to $ext_if port 80 \
>         rdr-to $server port 80 
>
> But when the redirection rule is tested from a client on the LAN, it doesn't work.

## Solution: [Split-Horizon DNS][]

Quoting again from the [OpenBSD pf FAQ][Split-Horizon DNS]:

> It's possible to configure DNS servers to answer queries from local hosts differently than external queries so that local clients will receive the internal server's address during name resolution. They will then connect directly to the local server, and the firewall isn't involved at all. This reduces local traffic since packets don't have to be sent through the firewall.

[Unbound-Views][] implements the [Split-Horizon DNS][] solution with a [Python][] plugin for the excellent [Unbound][] DNS resolver. This requires that the [Unbound][] DNS resolver has the [Python][] module installed and configured:

```
server:
  # chroot needs to be disabled otherwise
  # the python module will not load
  chroot: ""
  module-config: "validator python iterator"
python:
  # Full path to the Unbound-Views script file to load
  python-script: "/usr/local/etc/unbound/views.py"
```

[Unbound-Views][] Split-Horizon is configured with a [YAML][] file located in the same directory as the `views.py` plugin script:

```yaml
# ifs ## WAN subnet(s) #### LAN subnet(s) #
lan0:
       '169.254.10.0/25': '192.168.10.0/25'
       '169.254.20.0/25': '192.168.20.0/25'
```

The interface, `lan0` in the example above, needs to be the same as the interface that [Unbound][] is listening on facing the LAN. Both subnets, the WAN and the LAN side must be the same size.

When `ifconfig lan0` has an IPv4 address configured within the range of one of the LAN subnets, then any address within the range of the WAN subnet will be rewritten to a corresponding address within the LAN subnet.

For example, if the `lan0` interface is configured to `192.168.10.5` and a lookup resolves to `169.254.10.69` then `192.168.10.69` will be returned. However, since `lan0` does NOT have an IPv4 address within the 192.168.20.0/25 subnet, the second set of subnets will not be searched.  This allows for the same `views.yml` config file to be installed on multiple routers each configured on different LAN subnets and/or interface names.

The same [views.yml][] config file can be used on a machine where the `lan0` interface is configured with an address from the second LAN subnet. In that case the first set of subnets will be ignored and only the second set will be searched for split horizon candidates.

Unlike many other Split-Horizon Views implementations, [Unbound-Views][] does not require that anything special be configured and served by Authoritative DNS servers whether they are under your control or not.

[Unbound-Views][] has a convenient pf `rdr` generator which outputs an OpenBSD/pf syntax configuration file ready to pull in to `/etc/pf.conf` with an `include "/etc/pf.rdr"`:

    ~# python /usr/local/etc/unbound/views.py > /etc/pf.rdr

It's probably a good idea to edit out the redirects for the public IP address assigned to the edge router(s) and the broadcast address. Meaning the first and last redirects in the generated output. If using CARP, then most likely the first three or more redirects need to be omitted.

## Getting Started

* Install [Unbound][] with the [Python][] module enabled and configure as described above.
* Install [PyYAML][] and the [netaddr][] [Python][] modules required by [views.py][].
* Install [views.py][], [views.yml][] and this [README][] in [Unbound][]'s configuration folder.
* In [views.yml][] edit the interface name and the CIDR subnet ranges to reflect your actual setup.
* Configure pf (or the firewall of your choice) to portforward the redirects.
* Restart [Unbound][].
* Profit!!!

## License

See [LICENSE](https://GitHub.com/yds/unbound-views/blob/master/LICENSE).

[Redirection]:http://www.OpenBSD.org/faq/pf/rdr.html "PF: Redirection (Port Forwarding)"
[Reflection]:http://www.OpenBSD.org/faq/pf/rdr.html#reflect "Redirection and Reflection"
[Split-Horizon DNS]:http://www.OpenBSD.org/faq/pf/rdr.html#splitdns "Split-Horizon DNS"
[Unbound]:http://Unbound.net/ "Unbound is a validating, recursive, and caching DNS resolver"
[Python]:https://www.Python.org/ "Python is a great object-oriented, interpreted, and interactive programming language"
[netaddr]:https://PyPi.Python.org/pypi/netaddr "Pythonic manipulation of IPv4, IPv6, CIDR, EUI and MAC network addresses"
[PyYAML]:http://www.PyYAML.org/ "YAML Ain't Markup Language"
[YAML]:http://www.YAML.org/ "YAML Ain't Markup Language"
[README]:https://GitHub.com/yds/unbound-views/blob/master/README.md
[views.py]:https://GitHub.com/yds/unbound-views/blob/master/views.py
[views.yml]:https://GitHub.com/yds/unbound-views/blob/master/views.yml
[Unbound-Views]:https://GitHub.com/yds/unbound-views/ "Split-Horizon Views plugin for the Unbound DNS resolver"
