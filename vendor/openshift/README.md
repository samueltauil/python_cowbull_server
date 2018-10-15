### Deploying the Cowbull application (n-tier)

There are two options to deploy the Cowbull appplication, deploying each component manually or deploying all of them in one shot by using a template.

We will cover both ways, so let's start doing the manual process.

Before start we need to clone and move to the project directory.

```
git clone https://github.com/samueltauil/python_cowbull_server
```

```
cd python_cowbull_server
```
From here you can choose which way to go.

#### Deploying manually all components

Let's create a project first.

```
oc new-project cowbull-dev
```

Create the ConfigMap to store the cowbull config file.

```
oc create configmap cowbull-config --from-file vendor/kubeconfig/cowbull.cfg
```

Deploy Redis
```
oc create -f vendor/kubernetes/deploy-redis.yml
```

Create a new application by doing a Docker build and injecting the environment variables needed in the application to run.
```
oc new-app https://github.com/samueltauil/python_cowbull_server PERSISTENCE_ENGINE=redis REDIS_HOST=redis-master LOGGING_LEVEL=10 COWBULL_CONFIG=/cowbull/config/cowbull.cfg
```

Add a volume to mount the config file from the ConfigMap into the pod.

```
oc volume dc/pythoncowbullserver --overwrite --add -t configmap  -m /cowbull/config --name=cowbull-config --configmap-name=cowbull-config
```

Deploy the web application injecting the environment variables into runtime.

```
oc new-app dsanderscan/cowbull_webapp LOGGING_LEVEL=10 COWBULL_SERVER=pythoncowbullserver COWBULL_PORT=8080
```

#### Deploying using the Template

Make sure you are in the `python_cowbull_server` directory, then let's process the template to create the resources we need.

```
oc process -f vendor/openshift/cowbull_template.json | oc create -f -
```

Second option would be importing the template directly from the OpenShift web console and selecting it from the catalog.

### Extending to use the Jenkins Pipeline

Lets create the pipeline which will trigger a Jenkins instance deployment within the project.

```
oc create -f vendor/openshift/cowbull_buildconfig_pipeline.yml
```

Make sure you create a QA project called `cowbull-qa`.

```
oc new-project cowbull-qa
```

Then let's give the jenkins service account in the `cowbull-dev` project access and permission to create resources in the `cowbull-qa` project.

```
oc policy add-role-to-user edit system:serviceaccount:cowbull-dev:jenkins -n cowbull-qa
```

Now we will give the `image-puller` role to the serviceaccounts for the `cowbull-qa` into the `cowbull-dev` project.

```
oc policy add-role-to-group system:image-puller system:serviceaccounts:cowbull-qa -n cowbull-dev
```

Now just go to *Builds -> Pipelines* and click start.
