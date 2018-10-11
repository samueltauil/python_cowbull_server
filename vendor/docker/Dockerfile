FROM		python:3.5.3-slim
MAINTAINER	David Sanders
RUN			apt-get update && \
			groupadd -r cowbull_g && \
			mkdir /cowbull && \
			useradd -r -G cowbull_g -d /cowbull cowbull && \
			chown cowbull /cowbull
WORKDIR		/cowbull
COPY		requirements.txt /cowbull
RUN		    pip install -q setuptools
RUN		    pip install -q -r /cowbull/requirements.txt
USER		cowbull
ENV			PYTHONPATH="/cowbull"
COPY        extensions /cowbull/extensions/
COPY        flask_controllers /cowbull/flask_controllers/
COPY        flask_helpers /cowbull/flask_helpers
COPY	    Game	/cowbull/Game/
COPY        Persistence /cowbull/Persistence/
COPY        PersistenceExtensions /cowbull/PersistenceExtensions/
COPY	    python_cowbull_server /cowbull/python_cowbull_server/
COPY        Routes /cowbull/Routes
COPY        tests /cowbull/tests
COPY        app.py  /cowbull/
COPY        LICENSE /cowbull/
CMD			["gunicorn", "-b", "0.0.0.0:8080", "-w", "4", "app:app"]
EXPOSE		8080
