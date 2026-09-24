from pydantic import BaseModel,Field,IPvAnyAddress
from typing import Literal,Set,Union
from dataclasses import dataclass, field

class SessionInfo(BaseModel):
    page_size:int =  50
    current_page:int = 1
    create_time_num:int = 60
    create_time_type:str = "minute"
    forward_src:Union[IPvAnyAddress, Literal['']] = ''
    forward_dst:Union[IPvAnyAddress, Literal['']] = ''
    nat_src:str = ''
    nat_dst:str = ''
    forward_sport:str = ''
    forward_dport:str = ''
    nat_dport:str = ''
    nat_sport:str = ''
    pktsType:str = "two-way"
    pktsCompare:str = "more-then"
    pktsNum:str = ''
    src_if:str = ''
    dst_if:str =  ''
    proto:str = ''
    policy_name:str = ''
    app_desc: str = Field('', alias='appDesc[]')
    app:str =  ''

    model_config = {
        "populate_by_name": True  # 允许用字段名赋值
    }

class PolicyAction(BaseModel):
    name:str
    action:Literal["permit", "deny"] = "permit"


class StopCaptureReq(BaseModel):
    output_file: str | None = None
    mode: str = Literal["none", "ja","ip_filter",'ja_ip_filter']


@dataclass
class AppIP:
    name: str = ""
    ip: Set[str] = field(default_factory=set)

    def update(self, app_desc: str, ip_set: Set[str]):
        if app_desc == "":
            self.ip.clear()
        elif app_desc == self.name:
            self.ip.update(ip_set)
        else:
            self.name = app_desc
            self.ip = set(ip_set)