FROM ocrd/all:maximum

RUN git clone https://github.com/ocr-d/core.git && \
	cd core && \
	git checkout workflow-endpoint-logging-2023-09-26 && \
	make install && \
	. /usr/local/sub-venv/headless-tf1/bin/activate && \
	make install && \
	deactivate
RUN ocrd resmgr download ocrd-tesserocr-recognize Fraktur.traineddata
WORKDIR /data
