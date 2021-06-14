import yaml, logging, os
from kubernetes import client
from kubernetes import config, client
from src.settings import TMP_DIR
from k8s_user import CSRK8sUser

logging.basicConfig(level=logging.INFO ,
                    format='%(asctime)s - %(levelname)s - %(message)s')

def load_from_yaml(filename: str) -> dict:
    """
        Loads data from yaml file.
    """
    with open(filename) as f:
        data = yaml.safe_load(f)
    return data

def k8s_rb_namespaced_add(username: str,namespace: str ,role: str,api_client: client.ApiClient) -> None:
    """
       Create namespaced RoleBinding in Kubernetes cluster
    """
    rbac_api = client.RbacAuthorizationV1Api(api_client)
    body=load_from_yaml("src/template/namespaced-rb.yaml")
    body['metadata']['name']=f'{username}-{role}-RB'
    body['metadata']['namespace']=namespace
    body['subjects'][0]['name']=username
    body['roleRef']['name']=f'{namespace}-{role}'
    try: 
        logging.info(body)
        rbac_api.create_namespaced_role_binding(body=body,namespace=namespace)
    except client.exceptions.ApiException as x:
        logging.info(x.body)

def k8s_rb_cluster_add(username: str, role: str, api_client: client.ApiClient) -> None:
    """
       Create ClusterRoleBinding in Kubernetes cluster
    """
    rbac_api = client.RbacAuthorizationV1Api(api_client)
    if role == 'admin':
        k8s_clusterrole_add(username,api_client)
        role_name=f'{username}-R'
    else: role_name='allow-port-forward'
    body=load_from_yaml("src/template/cluster-rb.yaml")
    body['metadata']['name']=f'{username}-RB'
    body['subjects'][0]['name']=username
    body['roleRef']['name']=role_name
    try:
        rbac_api.delete_cluster_role_binding(name=body['metadata']['name'])
    except client.exceptions.ApiException as x:
        logging.info(x.body)
    logging.info(body)
    rbac_api.create_cluster_role_binding(body=body) 


def k8s_clusterrole_add(username: str, api_client: client.ApiClient) -> None:
    """
        Create ClusterRole in Kubernetes cluster
    """
    rbac_api = client.RbacAuthorizationV1Api(api_client)
    body=load_from_yaml("src/template/cluster-r.yaml")
    body['metadata']['name']=f'{username}-R'
    try:
        rbac_api.delete_cluster_role(name=body['metadata']['name'])
    except client.exceptions.ApiException as x:
        logging.info(x.body)
    logging.info(body)
    rbac_api.create_cluster_role(body=body)

def k8s_user_add(username: str, api_client: client.ApiClient) -> bool:
    """
        Create  CSR User in Kubernetes cluster and save his config in file.
        To use this function install https://github.com/JoeJasinski/k8s_user with pip install -e 
    """
    user = CSRK8sUser(name=username)
    inputs = {
        "cluster_name": "default",
        "context_name": "default",
        "out_kubeconfig": f'{TMP_DIR}/tmp_{username}_kubeconf',
        "creds_dir": TMP_DIR,
    }
    user.create(api_client, inputs)
    os.remove(f'{TMP_DIR}/{username}.crt.pem')
    os.remove(f'{TMP_DIR}/{username}.csr.pem')
    os.remove(f'{TMP_DIR}/{username}.key.pem')
    cert=client.CertificatesV1beta1Api(api_client)
    cert.delete_certificate_signing_request(name=username)
    return True
