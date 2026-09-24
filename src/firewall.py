import httpx
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_v1_5
from models import SessionInfo
from endpoints import APIEndpoints
import base64
from config import get_settings


class FireWallAPI():
    def __init__(self):
        settings = get_settings()
        self.host = settings.firewall_host
        self.user = settings.firewall_username
        self.pswd = settings.firewall_password
        self.success_code = 20000
        self.headers = {"Referer":self.host}
        self.endpoint = APIEndpoints(self.host)
        self.index = {}

    async def get_pubkey(self) -> str:
         async with httpx.AsyncClient(verify=False) as client:
             res_pubkey = await client.get(self.endpoint.public_key)
         self.pubkey = res_pubkey.json()['data']['details']
         return self.pubkey

    async def rsa_key(self,cert:str) -> str:
        # 获取公钥对象
        rsakey = RSA.import_key(f"{self.pubkey}")
        # 使用公钥加密明文
        cipher = PKCS1_v1_5.new(rsakey)
        cipher_text = cipher.encrypt(cert.encode('utf-8'))
        #编码
        cipher_text_decode=base64.b64encode(cipher_text).decode()
        return cipher_text_decode

    async def login(self) -> str:
        """return : cookie"""
        await self.get_pubkey()
        self.username,self.password = await self.rsa_key(self.user),await self.rsa_key(self.pswd)
        settings = get_settings()
        data = {
                "username":self.username,
                "password":self.password,
                "encrypt_disable":settings.rsa_encrypt_disable
              }

        async with httpx.AsyncClient(verify=False) as client:
            login_res = await client.post(self.endpoint.login,data=data)
        try:
            login_code = login_res.json()['code']
        except :
            raise IndexError("请求异常,请验证请求信息")
            
        assert login_code == self.success_code,f"Response code is {login_code}. Login Failed !"
        print(f'Login Web:[{self.host}] [{login_res.json()['msg']}]')
        sessionid=login_res.json()["data"]["sessionid"]
        csrftoken = login_res.headers['Set-cookie'].split(';')[0]
        cookie = f"LOCAL_LANG_i18n=zh;{csrftoken};sessionid={sessionid}"
        self.headers["Cookie"] = cookie
        return cookie
    
    async def get_session_info(self,session_info:SessionInfo)->dict:
        app = self.index.get(session_info.app_desc,'')
        session_info.app = app
        params = session_info.model_dump()
        async with httpx.AsyncClient(verify=False) as client:
            r = await client.get(self.endpoint.session_info,headers=self.headers,params=params)
        data = r.json()
        print(f"获取{app}会话信息 状态:{r}")
        if data['code'] == 20000:
            return data['data']
        else:
            print(f"获取会话信息失败:{data['msg']}")
            return data['msg']
        
    async def filter_session(self,sessions:dict) -> list[dict]:
        field_mapping = {'forward_src': '源地址',
                        'forward_dst': '目标地址', 
                        'forward_sport': '源端口',
                        'forward_dport': '目的端口',
                        'dst_if': '出接口',
                        'proto':'协议',
                        'app': '应用',
                        'policy_name': '安全策略'
                        }
        filtered_sessions = [{field_mapping[key]: session[key] for key in field_mapping.keys() 
                            if key in session}
                            for session in sessions]
        
        return filtered_sessions

    async def get_app_tree(self):
        async with httpx.AsyncClient(verify=False) as client:
            r = await client.get(self.endpoint.app_tree,headers=self.headers)
        return r.json()
    
    async def build_sub_class_index(self, tree):
        """desc_name 查 sub_class_name 建立快速索引"""
        self.index = {}
        for cls in tree['list']:
            for sub in cls['sub_class_list']:
                # 先添加sub本身的索引
                self.index[sub['desc_name']] = sub['sub_class_name']
                
                # 再遍历sub下的app_list
                for app in sub['app_list']:
                    self.index[app['desc_name']] = app['app_name']
        return self.index
    
    async def get_index(self):
        tree = await self.get_app_tree()
        if tree['code'] == self.success_code:
            index = await self.build_sub_class_index(tree['data'])
            return index
        else:
            return tree['msg']
        
    async def logout(self):
        async with httpx.AsyncClient(verify=False) as client:
            r = await client.get(self.endpoint.logout,headers=self.headers)
            return r.json()
        
    async def add_policy_action(self,name:str,action:str):
        """添加策略"""
        policy_info = {"security_policy":[{"name":name,"action":action}],"is_sim":0,"c_state":action}
        async with httpx.AsyncClient(verify=False) as client:
            r = await client.post(self.endpoint.add_policy,headers=self.headers,json=policy_info)
        return r.json()
    
firewall = FireWallAPI()