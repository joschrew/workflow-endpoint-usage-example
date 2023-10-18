# This is for if a core branch should be used with ocrd-all-image
# currently not needed but left as template
FROM ocrd/all:maximum

RUN git clone https://github.com/ocr-d/core.git && \
	cd core && \
	git checkout network-log-refactoring && \
	make install && \
	. /usr/local/sub-venv/headless-tf1/bin/activate && \
	make install && \
	deactivate
WORKDIR /data
