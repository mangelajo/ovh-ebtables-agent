%global commit fceb3729858b3d65f6c96e815dddeafeedb4a5c3 
%global shortcommit %(c=%{commit}; echo ${c:0:7})

Name:           ovh-ebtables-agent
Version:        2014.2
Release:        1%{?dist}
Summary:        OpenStack Networking agent to work with OVH network

Group:          Applications/System
License:        ASL 2.0
URL:            https://github.com/mangelajo/ovh-ebtables-agent 

Source0:        https://github.com/mangelajo/ovh-ebtables-agent/archive/%{commit}/ovh-ebtables-agent-%{commit}.tar.gz

BuildArch:      noarch

BuildRequires:  python-setuptools
BuildRequires:  systemd-units
BuildRequires:  python-pbr

Requires:       openstack-neutron
Requires(post): systemd-units
Requires(preun): systemd-units
Requires(postun): systemd-units

%description
OVH ebtables agent is an agent to make neutron networking possible
in OVH network.

%prep
%setup -qn %{name}-%{commit}

%build
git init . # ugly workaround for pbr..
%{__python} setup.py build

%install
%{__python} setup.py install -O1 --skip-build --prefix %{_prefix} --root %{buildroot} 

# Move config files to proper location
install -d -m 755 %{buildroot}%{_sysconfdir}/neutron
install -d -m 755 %{buildroot}%{_sysconfdir}/neutron/rootwrap.d
mv %{buildroot}/usr/etc/neutron/*.ini %{buildroot}%{_sysconfdir}/neutron
mv %{buildroot}/usr/etc/neutron/rootwrap.d/* %{buildroot}%{_sysconfdir}/neutron/rootwrap.d/

%post
if [ $1 -eq 1 ] ; then
    # Initial installation
    /bin/systemctl daemon-reload >/dev/null 2>&1 || :
fi

%preun
if [ $1 -eq 0 ] ; then
    # Package removal, not upgrade
    /bin/systemctl --no-reload disable ovh-ebtables-agent.service > /dev/null 2>&1 || :
    /bin/systemctl stop ovh-ebtables-agent.service > /dev/null 2>&1 || :
fi


%postun
/bin/systemctl daemon-reload >/dev/null 2>&1 || :
if [ $1 -ge 1 ] ; then
    # Package upgrade, not uninstall
    /bin/systemctl try-restart ovh-ebtables-agent.service >/dev/null 2>&1 || :
fi


%files
%doc LICENSE
%doc README.md
%{_bindir}/ovh-ebtables-agent
%{_bindir}/ovh-bridge-eth
%{_unitdir}/ovh-ebtables-agent.service
%dir %{_sysconfdir}/neutron
%config(noreplace) %attr(0640, root, neutron) %{_sysconfdir}/neutron/ovh_ebtables_agent.ini
%dir %{_sysconfdir}/neutron
%dir %{_sysconfdir}/neutron/rootwrap.d
%config(noreplace) %{_sysconfdir}/neutron/rootwrap.d/*
%{python_sitelib}/ovhagent-%{version}*.egg-info
%{python_sitelib}/ovhagent/*


%changelog
* Fri Dec 5 2014 Miguel Angel Ajo <miguelangel@ajo.es> 2014.2.1-1
- Initial package release 

