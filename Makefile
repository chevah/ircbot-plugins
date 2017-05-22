all: test
	

clean:
	rm -rf build

env:
	@if [ ! -d "build" ]; then virtualenv build; fi


deps: env
	@build/bin/pip install -Ue '.[dev]'
	mkdir build/run
	mkdir build/run/logs
	mkdir build/run/data
	mkdir build/run/conf


run:
	cp robi-net.conf.seed build/robi-net.conf
	@build/bin/supybot --debug build/robi-net.conf

irc-bot-oauth:
	@build/bin/python limnoria-plugins/SupportNotifications/make_credentials.py \
		client_id.json \
		build/run/credentials.json


lint:
	@build/bin/pyflakes chevah/ scripts/ limnoria-plugins/
	@build/bin/pep8 chevah/ scripts/ limnoria-plugins/


test: lint
	@build/bin/python setup.py test
