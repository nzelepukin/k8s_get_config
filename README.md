
## PreDeploy
```
kubectl apply -f k8s_deploy/get-config-cm.yaml -n my-namespace
kubectl create sa k8s-get-config-sa -n my-namespace
kubectl apply -f k8s_deploy/get-config-sa-R.yaml
Edit namespace in k8s_deploy/get-config-sa-RB.yaml
kubectl apply -f k8s_deploy/get-config-sa-RB.yaml
Edit k8s_deploy/deployment.yaml with your variables, ingress URL and ingress annotations.
kubectl apply -f k8s_deploy/deployment.yaml -n my-namespace

```

## Virtual environments
```dotenv
APP_PORT=8080
TMP_DIR= path to folder for temorary files
KUBE_API_URL='https://1.2.3.4:6443'
LDAP_SERVER= DNS or IP address of your LDAP server
LDAP_DOMAIN= LDAP domain name
```

## Usage
When you need to create or edit some user in cluster just edit ConfigMap (get-config-cm). Restart pod and send application URL to user.
![How it looks](https://github.com/nzelepukin/k8s_get_config/blob/master/UI.png?raw=true)


## Health check

Returns `200` on `/`
