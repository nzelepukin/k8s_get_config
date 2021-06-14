import os, json, asyncio, logging
from aiohttp import web
from src.settings import APP_PORT,TMP_DIR,KUBE_API_URL,LDAP_SERVER,LDAP_DOMAIN
from src.utils import load_from_yaml, k8s_rb_cluster_add, k8s_rb_namespaced_add, k8s_user_add
from ldap3 import Server, Connection
from kubernetes import client

logging.basicConfig(level=logging.INFO ,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def create_app() -> web.Application:
    """
        Create web application instance with routes etc.
    """
    loop= asyncio.get_event_loop()
    app = web.Application()
    app.router.add_get('/', login)
    app.router.add_get('/login.css', css)        
    app.router.add_get('/user-icon.png', img)
    app.router.add_post('/get_config', main_workflow)
    return app

def start_webapp() -> None:    
    """
        Start web application instance
    """     
    app = create_app()
    web.run_app(app, host='0.0.0.0', port=APP_PORT)

## Handlers for ststic pages and scripts to avoid making additional Frontend'а
async def login(request):
    return web.FileResponse('./src/frontend/login.html')
async def css(request):
    return web.FileResponse('./src/frontend/login.css')
async def img(request):
    return web.FileResponse('./src/frontend/user-icon.png')
###

def k8s_register() -> client.ApiClient :
    """
        Authenticating in Kubernetes cluster with service account credentials
    """
    with open('/run/secrets/kubernetes.io/serviceaccount/token') as f:
        token=f.read()
    configuration = client.Configuration()
    configuration.api_key["authorization"] = token
    configuration.api_key_prefix['authorization'] = 'Bearer'
    configuration.host = KUBE_API_URL
    configuration.ssl_ca_cert = '/run/secrets/kubernetes.io/serviceaccount/ca.crt'
    api_client = client.ApiClient(configuration=configuration)
    return api_client

async def main_workflow(request: web.BaseRequest) -> web.FileResponse:
    """
        Main workflow, user request comes here. 
        Function check user in LDAP and ConfigMap. Then create user with config and add permissions.
    """
    data = await request.json()
    api_client=k8s_register()
    username = data['username']
    password = data['password']
    logging.info(f'Checking {username} with LDAP server')
    if not check_ldap_user(username,password):
        return web.HTTPUnauthorized(reason='User not found in LDAP')
    app_config=load_from_yaml('config/config.yml')['users']
    if not username in app_config:
        return web.HTTPUnauthorized(reason='User not found in ConfigMap')
    if not k8s_user_add(username,api_client):
        return web.HTTPError(reason='Cant create user')
    create_user_permissions(username,app_config,api_client)
    return web.FileResponse(f'{TMP_DIR}/tmp_{username}_kubeconf')

def check_ldap_user(username: str, password: str)-> bool:
    """
        Check user existence in LDAP.
    """
    server =Server(LDAP_SERVER)
    username = f"{LDAP_DOMAIN}\\{username}"
    try:
        with Connection(server, user=username, password=password) as conn:
            return True
    except:
        return False

def create_user_permissions(username: str, app_config: dict,api_client: client.ApiClient) -> None:
    """
        Add permissions to user in Kubernetes cluster
    """
    if app_config[username]['cluster']['admin']: k8s_rb_cluster_add(username,'admin',api_client)
    if app_config[username]['cluster']['read-pf']: k8s_rb_cluster_add(username,'read-pf',api_client)
    for ns in app_config[username]['namespace']:
        if ns['pods-r']: k8s_rb_namespaced_add(username,ns['name'],'pods-r',api_client)
        if ns['port-forward']: k8s_rb_namespaced_add(username,ns['name'],'port-forward',api_client)
        if ns['admin']: k8s_rb_namespaced_add(username,ns['name'],'admin',api_client)


if __name__ == '__main__':
    start_webapp()