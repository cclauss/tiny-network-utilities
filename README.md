# tiny-dhcp-server
Simple DHCP server for FreeBSD

# What is tiny-dhcp-server?
This is the minimalistic DHCP server implementation for FreeBSD (has some OS-specific parts).

It responds on one specified network interface, allocates the new IP address for each server, and assigns itself as the default gateway and DNS.

# What is it good for?
It is originally designed to be able to initialize the virtual machine network (tapN) when VM is connected to the host through the bridged interface.

# Requirements
* FreeBSD (tested on 10.1)
* Python 3 installed (tested with python34-3.4.3)
* net/py-netifaces package installed for Python 3 (py34-netifaces-0.10.3)

# How do I run it?
Here is an example:

\# tiny-dhcp-server.py tap0
