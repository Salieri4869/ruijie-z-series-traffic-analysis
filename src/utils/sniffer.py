from scapy.all import AsyncSniffer,wrpcap,conf
from scapy.utils import wrpcap
from pathlib import Path
from scapy.plist import PacketList
from scapy.layers.inet import IP
import asyncio
from collections import defaultdict

class Sniffer:
    def __init__(self, interface, filter_str, queue:asyncio.Queue):
        self.interface = interface
        self.filter_str = filter_str
        self.queue = queue
        self.ip_filtered_path = Path("ip_filtered_pcaps")
        self.ip_filtered_path.mkdir(exist_ok=True)
        self.sniffer = AsyncSniffer(iface=self.interface, filter=self.filter_str, prn=self.packet_callback)

    def start(self):
        self.sniffer.start()

    def stop(self):
        self.sniffer.stop()

    def packet_callback(self, packet):
        self.queue.put_nowait(str(packet))

    def save_pcap(self,output_file:str='Capture Session.pcap'):
        wrpcap(output_file, self.sniffer.results)

    def save_filtered_pcap(self,file_name:str,ips:set):
        packet:PacketList = self.sniffer.results
        ip_to_pkts = defaultdict(list)
        output_path = self.ip_filtered_path / file_name
        output_path.mkdir(exist_ok=True)

        for p in packet:
            if IP in p:
                src, dst = p[IP].src, p[IP].dst
                for ip in {src, dst} & ips:
                    ip_to_pkts[ip].append(p)

        for ip, pkts in ip_to_pkts.items():
            wrpcap(str(output_path / f"{file_name}_{ip}.pcap"), pkts)

if __name__ == '__main__':
    sniffer = Sniffer(interface=conf.iface, filter_str=None)
    sniffer.start()
    input("Press Enter to stop sniffer...")
    sniffer.stop()
    sniffer.save_pcap(output_file='Capture Session.pcap')