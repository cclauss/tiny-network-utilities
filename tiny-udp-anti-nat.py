#!/usr/local/bin/python3.4

# Copyright (C) 2015 by Yuri Victorovich. All rights reserved.
# This code is licensed under BSD license.

##
## tiny-udp-anti-nat
##
## This is the UDP packet filter that changes the destination ip and port of USB
## packets in both directions. It gets UDP packets from the divert socket
## provided by the firewall rules.
##

## Sample divert ipfw rules
#$ipfw 03055 divert 03056 log udp from 1.1.1.2 to any in via tap1
#$ipfw 03056 divert 03056 log udp from 1.1.1.1 to any out via tap1
#$ipfw 03057 allow log udp from 1.1.1.0/24 to 1.1.1.1 in via tap1
#$ipfw 03058 allow log udp from 1.1.1.1 to 1.1.1.0/24 out via tap1

import sys, getopt
import socket
import struct
import net_checksums

# missing constants
socket_IPPROTO_DIVERT=258


##
## Command line arguments and usage
##

arg_clnt_divert_ip = "1.1.1.1"
arg_clnt_divert_port = 0
do_ip = False
do_port = False
arg_ip_old = None
arg_ip_new = None
arg_port_old = 0
arg_port_new = 0

def usage():
    print('%s -d <divert-port> -i <old-dst-ip>:<new-dst-ip> -p <old-dst-port>:<new-dst-port>' % (sys.argv[0]))
    sys.exit(2)

def ip_str_to_bytes(ip):
    #return bytes([hex(int(x)) for x in ip.split('.')])
    return bytes([int(x) for x in ip.split('.')])

try:
    opts, args = getopt.getopt(sys.argv[1:], "d:i:p:",["divert=", "ip=","port="])
except getopt.GetoptError:
    usage()
for opt,arg in opts:
    if opt in ("-d", "--divert"):
        arg_clnt_divert_port = int(arg)
    elif opt in ("-i", "--ip"):
        ip_spec = arg.split(':')
        if do_ip or len(ip_spec) != 2:
            usage()
        arg_ip_old = ip_str_to_bytes(ip_spec[0])
        arg_ip_new = ip_str_to_bytes(ip_spec[1])
        do_ip = True
    elif opt in ("-p", "--port"):
        port_spec = arg.split(':')
        if do_port or len(port_spec) != 2:
            usage()
        arg_port_old = int(port_spec[0])
        arg_port_new = int(port_spec[1])
        do_port = True
if arg_clnt_divert_port == 0 or (not do_ip and not do_port):
    usage()

##
## procedures
##

def unpack_ip(pkt, off):
    return pkt[off:off+4]

def unpack_ip_src(pkt):
    return unpack_ip(pkt, 12)

def unpack_ip_dst(pkt):
    return unpack_ip(pkt, 16)

def pack_ip(pkt, off, ip):
    pkt[off:off+4] = ip

def pack_ip_src(pkt, ip):
    pack_ip(pkt, 12, ip)

def pack_ip_dst(pkt, ip):
    pack_ip(pkt, 16, ip)

def unpack_port(pkt, off):
    return socket.ntohs(struct.unpack('H', pkt[off:off+2])[0])

def unpack_port_src(pkt):
    return unpack_port(pkt, 20)

def unpack_port_dst(pkt):
    return unpack_port(pkt, 22)

def pack_port(pkt, off, port):
    pkt[off:off+2] = struct.pack('H', socket.htons(port))

def pack_port_src(pkt, port):
    pack_port(pkt, 20, port)

def pack_port_dst(pkt, port):
    pack_port(pkt, 22, port)

def create_sock_divert(ip,port):
    sock = socket.socket(socket.AF_INET, socket.SOCK_RAW, socket_IPPROTO_DIVERT)
    sock.bind((ip, port))
    return sock

def is_dir_match(pkt):
    return (not do_ip or unpack_ip_dst(pkt)==arg_ip_old) \
        and (not do_port or unpack_port_dst(pkt)==arg_port_old)

def is_rev_match(pkt):
    return (not do_ip or unpack_ip_src(pkt)==arg_ip_new) \
        and (not do_port or unpack_port_src(pkt)==arg_port_new)

def update_dir(pkt):
    if do_ip:
        pack_ip_dst(pkt, arg_ip_new)
    if do_port:
        pack_port_dst(pkt, arg_port_new)

def update_rev(pkt):
    if do_ip:
        pack_ip_src(pkt, arg_ip_old)
    if do_port:
        pack_port_src(pkt, arg_port_old)

##
## MAIN cycle
##

sock = create_sock_divert(arg_clnt_divert_ip, arg_clnt_divert_port)

# main event loop
while True:
    (pkt, addr) = sock.recvfrom(64000, 1024)
    pkt = bytearray(pkt)
    print('received addr=%s' % (str(addr)))
    # process
    if is_dir_match(pkt):
        print('replacing OLD->NEW')
        update_dir(pkt)
    elif is_rev_match(pkt):
        print('replacing NEW->OLD')
        update_rev(pkt)
    else:
        print('unknown packet received: %s:%d -> %s:%d' % (unpack_ip_src(pkt), unpack_port_src(pkt), unpack_ip_dst(pkt), unpack_port_dst(pkt)))
        print('... dst-ip-old=%s' % (arg_ip_old))
    # recompute checksum
    net_checksums.checksum_calc_udp_packet(pkt)
    # send further
    sock.sendto(pkt, addr)

