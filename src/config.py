from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache


class Settings(BaseSettings):
    # ===== 防火墙配置 =====
    firewall_host: str = "https://192.168.66.1"
    firewall_username: str = "admin"
    firewall_password: str = ""

    # RSA 加密配置
    rsa_encrypt_disable: bool = True

    # ===== 抓包配置 =====
    sniffer_interface: str = "Realtek Gaming 2.5GbE Family Controller"
    sniffer_filter: str = "not arp and host 192.168.66.2 and host not 192.168.66.1"

    # ===== 应用配置 =====
    page_title: str = "Z系列防火墙管理系统"
    debug: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,   # 环境变量不区分大小写
        extra="ignore",         # 忽略未声明的多余变量
    )

@lru_cache()
def get_settings() -> Settings:
    """全局单例：应用启动时加载一次 .env，后续直接复用。"""
    return Settings()
