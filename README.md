# python_cowbull_server

**Version 1.0**

This is part 3 of a multi-part tutorial. The link for the tutorial will be provided soon.
This is an open source project and you are welcome to reuse and/or fork it.

**Related Projects**
* [python_digits](https://github.com/dsandersAzure/python_digits) : The python_digits object
used as the base of this game.
* [python_cowbull_game](https://github.com/dsandersAzure/python_cowbull_game) : A Flask
based server which serves up a web server offering the game to callers (human or machine)
* [python_cowbull_console](https://github.com/dsandersAzure/python_cowbull_console) : A
console based game which interacts with the server
* [python_cowbull_webapp](https://github.com/dsandersAzure/python_cowbull_webapp) : A single
page webapp which interacts with the web server using XHR (XMLHttpRequest).

Python cowbull server is a Flask based http server that serves the
cowbull game using python_cowbull_game objects. It serves up the game
by responding to http requests to ``http://server/version/game`` and
decides the action based on the method used for the request: ``GET`` starts
a new game and ``POST`` makes a guess against the game.

### Swagger Definition
coming soon.

### Depdendencies
The game requires a Redis server to act as a cache for game object information
and must be configured before running the game. The game picks up the Redis
server via env vars:

* REDIS_HOST : Defines the fqdn name of the redis host (e.g. redis)
* REDIS_PORT : Defines the port number redis is listening on (e.g. 6379)
* REDIS_DB : Defines the database number (e.g. 0)
* REDIS_USEAUTH : *Not Currently Used* For future use to tell the game 
server to use redis authentication.

Any redis server will do and options include:
1. [Redis Labs](https://redislabs.com/) free service with 30MB
2. Docker - use `docker run --name redis -p 6379:6379 -d redis`
3. Kubernetes - use the K8s instructions below

### Running the game
To run the game server using source, follow these steps (assuming using Docker for Redis):
```
virtualenv /path/to/virtual/env --python=python3
source /path/to/virtual/env/bin/activate
export REDIS_HOST="localhost"
export REDIS_PORT=6379
export FLASK_HOST="0.0.0.0"
export FLASK_PORT=5000
export FLASK_DEBUG="true"
docker run --name redis -p 6379:6379 -d redis
cd /to/location/repo/installed
python app.py
```

To run the game server using Docker, follow these steps:
```
cd /to/location/repo/installed
docker build -t imagename -f vendor/docker/Dockerfile .
docker network create yournetwork --driver bridge
docker run --name redis --network yournetwork -d redis
docker run --name cowbull --network yournetwork --env REDIS_HOST="redis" -p 5000:5000 -d {imagename}
#
# Tear down
#
docker stop redis
docker rm redis
docker stop cowbull
docker rm cowbull
```

To run the game using local Kubernetes (minikube) *NOTE* This uses 
the standard Docker image for the game server (dsanderscan/cowbull_v5):
```
minikube start
cd /to/location/repo/installed
kubectl create configmap cowbull-config --from-file vendor/kubeconfig/cowbull.cfg
kubectl create -f vendor/kubernetes/deploy-redis.yml
kubectl create -f vendor/kubeconfig/configured-cowbull.yml
kubectl get po # See the pods and wait till they are running
kubectl get svc
# NAME           CLUSTER-IP   EXTERNAL-IP   PORT(S)          AGE
# cowbull-svc    {ip addr.}   <pending>     5000:{port}/TCP   9s
#
# Use the minikube address (usually 192.168.99.100) and the port mapped
# to 5000 in the get svc output for requests.
#
# Tear down
#
kubectl delete -f vendor/kubernetes/deploy-redis.yml
kubectl delete -f vendor/kubeconfig/configured-cowbull.yml
#
# To remove configuration
#
kubectl delete configmap cowbull-config
```

### Requests
Make a request by issuing GET or POST methods to:
* `curl http://FLASK_HOST:FLASK_PORT/v0_1/game`

For added benefit, install [jq](https://stedolan.github.io/jq/) to be able 
to parse the JSON returned by the request:
* `curl -s <-X {method}> http://FLASK_HOST:FLASK_PORT/v0_1/game | jq`

**_Notes_**: 
1. If using Kubernetes:
  * Use your minikube node address (typically 192.168.99.100 and found
by executing `kubectl describe nodes minikube | grep Addresses | grep -v grep`) 
for FLASK_HOST
  * Use the port number found above (`kubectl get svc cowbull-svc`)
2. If using Docker:
  * Use `localhost` for FLASK_HOST
  * Use the port number `5000` for FLASK_PORT


### Methods
#### GET
Request (or get) a new game. An optional parameter mode
can be provided and state one of the game modes (easy, normal,
or hard).
* curl -s http://FLASK_HOST:FLASK_PORT/v0_1/game | jq
  ```
  {
    "digits": 4,
    "guesses": 10,
    "served-by": "{FLASK_HOST}",
    "key": "{uuid}"
  }
  ```
* curl -s http://FLASK_HOST:FLASK_PORT/v0_1/game?mode=easy | jq
  ```
  {
    "digits": 3,
    "guesses": 15,
    "served-by": "{FLASK_HOST}",
    "key": "{uuid}"
  }
  ```
* curl -s http://FLASK_HOST:FLASK_PORT/v0_1/game?mode=hard | jq
  ```
  {
    "digits": 6,
    "guesses": 6,
    "served-by": "{FLASK_HOST}",
    "key": "{uuid}"
  }
  ```

#### POST
Make a guess against an existing game, passing the key and
an array of Digits (integers between 0 and 9) as raw JSON data.

* curl -s -X POST -H "Content-type: application/json" -d '{"key":"{uuid}", "digits":[0, 1, 2, 3, 4, 5]}' http://localhost:5000/v0_1/game | jq
  ```
  {
    "served-by": "{FLASK_HOST}",
    "outcome": {
      "cows": 2,
      "status": "playing",
      "bulls": 1,
      "analysis": [
        {
          "multiple": false,
          "in_word": true,
          "index": 0,
          "digit": 0,
          "match": false
        },
        {
          "multiple": false,
          "in_word": true,
          "index": 1,
          "digit": 1,
          "match": false
        },
        {
          "multiple": false,
          "in_word": false,
          "index": 2,
          "digit": 2,
          "match": false
        },
        {
          "multiple": false,
          "in_word": true,
          "index": 3,
          "digit": 3,
          "match": true
        },
        {
          "multiple": false,
          "in_word": false,
          "index": 4,
          "digit": 4,
          "match": false
        },
        {
          "multiple": false,
          "in_word": false,
          "index": 5,
          "digit": 5,
          "match": false
        }
      ]
    },
    "game": {
      "mode": "hard",
      "ttl": 1494962909,
      "status": "playing",
      "key": "{uuid}",
      "guesses_made": 1,
      "guesses_remaining": 5
    }
  }
  ```
* Errors will be reported back to the caller via JSON.
  * Incorrect number of digits:
  ```
  {
  "module": "GameServerController",
  "exception": "The digits provided did not match the required number (6)",
  "method": "post",
  "message": "There was a problem with the value of the digits provided!",
  "status": 400
  }
  ```
  * Bad key:
  ```bash
  {
    "module": "GameServerControllerroller",
    "exception": "'The key provided is invalid.'",
    "method": "post",
    "message": "The request must contain a valid game key.",
    "status": 400
  }
  ```
  * Bad JSON data:
  ```
  {
    "moduGameServerControllerroller",
    "exception": "Failed to decode JSON object: Expecting value: line 1 column 1 (char 0)",
    "method": "post",
    "message": "Bad request. There was no JSON present. ### LIKELY CALLER ERROR ###",
    "status": 400
  }
  ```
  