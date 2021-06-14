VERSION ?= "0.0.1"

build:
	docker build -t k8s_user:${VERSION} . 


test: build
	docker run \
		-v `pwd`:/srv/ \
		-it k8s_user:${VERSION} \
		bash -c \
		"pytest -vv --cov-config=.coveragerc --cov=k8s_user tests/ \
			&& coverage html -d reports/"


shell: build
	docker run \
		-v `pwd`:/srv/ \
		-it k8s_user:${VERSION} \
		bash


clean: build
	rm -rf dist/ build kubernetes_user.egg-info/
	docker run \
		-v `pwd`:/srv/ \
		-it k8s_user:${VERSION} \
		bash -c "rm -rf .coverage reports/ .pytest_cache/ \
			&& find . -name '*.pyc' -exec rm -f {} \;"


package:
	python setup.py sdist bdist_wheel