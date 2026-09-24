import pyshark
from pyshark.packet.packet import Packet
import os
from pathlib import Path
from typing import List, Dict, Any
import time


class JaFilter:
    def __init__(self):
        self.ja_out_path = Path("results_ja")
        self.display_filter = "tls.handshake.ja3 or tls.handshake.ja4"
        os.makedirs(self.ja_out_path, exist_ok=True)

    def filter_ja(self, packets:List[Packet]) -> List[Dict[str, Any]]:
        ja_packets = (self.parse_ja(packet) for packet in packets)
        valid_results = (r for r in ja_packets if r.get("ja3") or r.get("ja4"))
        return list({tuple(sorted(r.items())): r for r in valid_results}.values())

    @staticmethod
    def parse_ja(packet:Packet) -> dict:
        match packet.highest_layer:
            case "TLS":
                ip = packet.ip.dst
                server_name = getattr(packet.tls, 'handshake_extensions_server_name', None)
                ja3 = getattr(packet.tls, 'handshake_ja3', None)
                ja4 = getattr(packet.tls, 'handshake_ja4', None)
            case "QUIC":
                ip = packet.ip.dst
                server_name = getattr(packet.quic, 'tls_handshake_extensions_server_name', None)
                ja3 = getattr(packet.quic, 'handshake_ja3', None)
                ja4 = getattr(packet.quic, 'handshake_ja4', None)
            case _:
                ip = server_name = ja3 = ja4 = None

        return {"ip":ip,"server_name":server_name,"ja3":ja3,"ja4":ja4}
    
    def save_ja_results_to_txt(self,results: List[Dict[str, Any]], filename: str):
        with open(self.ja_out_path/filename, 'w', encoding='utf-8') as f:
            for i, result in enumerate(results, 1):
                content = (f"[NO {i:02d}]\n"
                           f"[IP:  {result.get('ip', 'N/A')}]\n"
                           f"[SNI: {result.get('server_name', 'N/A')}]\n"
                           f"[JA3:{result.get('ja3', 'N/A')}]\n"
                           f"[JA4:{result.get('ja4', 'N/A')}]\n"
                           f"{'─' * 50}\n"
                           )
                f.write(content)

    def save_ja_fiter_to_txt(self,results: List[Dict[str, Any]], filename: str,ip_filter_list:list,distinct_ja:bool=False):
        """
        distinct_ja: ja去重
        """
        filter_results = [result for result in results if (ip := result.get('ip')) in ip_filter_list]
        with open(self.ja_out_path/filename, 'w', encoding='utf-8') as f:
            ja3_list = [f"[JA3: {ja3}]" for result in filter_results if (ja3 := result.get('ja3'))]
            ja4_list = [f"[JA4: {ja4}]" for result in filter_results if (ja4 := result.get('ja4'))]
            ip_list = [f"{ip}" for result in filter_results if (ip := result.get('ip'))]
            server_name_list = [f"{server_name}" for result in filter_results if (server_name := result.get('server_name'))]
            if distinct_ja:
                ja3_list = list(set(ja3_list))
                ja4_list = list(set(ja4_list))
                ip_list = list(set(ip_list))
                server_name_list = list(set(server_name_list))
            # 写入文件
            f.write("=== JA3 指纹列表 ===\n")
            f.write("\n".join(ja3_list))
            f.write("\n=== JA4 指纹列表 ===\n")
            f.write("\n".join(ja4_list))
            # f.write("\n\n=== IP 列表 ===\n")
            # f.write("\n".join(ip_list))
            # f.write("\n\n=== Server Name 列表 ===\n")
            # f.write("\n".join(server_name_list))


    def main(self,cap_file:Path,ip_filter_list:list,distinct_ja:bool=False):
        start_time = time.time()
        print("🔹 开始解析 pcap/cap 文件⏳")
        try:
            cap = pyshark.FileCapture(cap_file,display_filter=self.display_filter)
            items = self.filter_ja(cap)
            cap.close()
            if ip_filter_list:
                self.save_ja_fiter_to_txt(items, f"{cap_file.stem.split(' ')[0]}.txt",ip_filter_list,distinct_ja=True)
            else:
                self.save_ja_results_to_txt(items, f"{cap_file.stem.split(' ')[0]}.txt")
            print(f"✅ 成功解析 - {cap_file.name}")
        except Exception as e:
            print(f"❌ 解析失败 - {cap_file.name} - {e}")

        print(f"🔹 解析完成，用时 {time.time() - start_time:.2f} 秒")


pass
