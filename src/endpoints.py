
class APIEndpoints:
    """专用的端点配置类"""
    def __init__(self, host: str):
        self.host = host.rstrip('/')
    
    @property
    def public_key(self) -> str:
        return f"{self.host}/api/v1/public_key/"
    
    @property
    def login(self) -> str:
        return f"{self.host}/api/v1/login/"
     
    @property
    def logout(self) -> str:
        return f"{self.host}/api/v1/logout/"   

    @property
    def app_tree(self) -> str:
        return f"{self.host}/api/v1/application/tree/"
    
    @property
    def session_info(self) -> str:
        return f"{self.host}/api/v1/flow_monitor/session_monitor/getSessionInfo/"
    
    @property
    def add_policy(self) -> str:
        return f"{self.host}/api/v1/policy/add_policy/"
    
    @property
    def delete_policy(self) -> str:
        return f"{self.host}/api/v1/policy/delete_policy/"
    
    @property
    def get_policy(self) -> str:
        return f"{self.host}/api/v1/policy/get_policy/"