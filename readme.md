This are instructions how to use [the workflow endpoint](https://github.com/OCR-D/core/pull/1083)

1. Clone this repo and start all containers needed for the workflow (processing-server, mongoDb, rabbitMq, processing-workers)
```
git clone https://github.com/joschrew/workflow-endpoint-usage-example.git
cd workflow-endpoint-usage-example
# It is assumed ocrd/all:maximum is already there otherwise: docker pull ocrd/all:maximum
# the `data`-directory is used for providing the workspace to all processing-workers
docker-compose up -d ocrd-processing-server ocrd-mongodb ocrd-rabbitmq ocrd-cis-ocropy-binarize ocrd-anybaseocr-crop ocrd-cis-ocropy-denoise ocrd-tesserocr-segment-region ocrd-segment-repair ocrd-cis-ocropy-clip ocrd-cis-ocropy-segment ocrd-cis-ocropy-dewarp ocrd-tesserocr-recognize
```

2. Provide the workspace<br/>
copy the workspace to the data folder so that the mets is available at data/mets.xml

3. Run a workflow
```
curl -v -X POST "localhost:8000/workflow?mets_path=/data/mets.xml&page_wise=True" -H "Content-type: multipart/form-data" -F "workflow=@test-workflow.txt"
```

