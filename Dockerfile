FROM ocrd/all:maximum

RUN git clone https://github.com/ocr-d/core.git && \
	cd core && \
	git checkout workflow-endpoint && \
	make install
WORKDIR /data
