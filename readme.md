This are instructions how to use [the workflow endpoint](https://github.com/OCR-D/core/pull/1083)

1. Clone this repo and start needed containers (mongoDb, rabbitMq, processing-workers)
```
git clone https://github.com/joschrew/workflow-endpoint-usage-example.git
cd workflow-endpoint-usage-example
# It is assumed ocrd/all:maximum is already there otherwise: docker pull ocrd/all:maximum
# the `data`-directory is used for providing the workspace to all processing-workers
docker build -t ocrd_all_workflow .
docker-compose up -d ocrd-mongodb ocrd-rabbitmq ocrd-olena-binarize ocrd-anybaseocr-crop ocrd-cis-ocropy-denoise ocrd-tesserocr-segment-region ocrd-segment-repair ocrd-cis-ocropy-clip ocrd-cis-ocropy-segment ocrd-cis-ocropy-dewarp ocrd-tesserocr-recognize
```

2. Clone and install core to a venv:
```
git clone https://github.com/OCR-D/core.git
cd core
git switch workflow-endpoint
python3.8 -m venv venv
. venv/bin/activate
make install-dev
```

3. Start processing server
```
cat > my-test-config.yaml << "EOF"
internal_callback_url: http://172.17.0.1:8080
process_queue:
  address: localhost
  port: 5672
  skip_deployment: true
  credentials:
    username: admin
    password: admin
database:
  address: localhost
  port: 27018
  skip_deployment: true
  credentials:
    username: admin
    password: admin
hosts: []
EOF

ocrd network processing-server my-test-config.yaml -a 0.0.0.0:8080
```

4. Switch back to `workflow-endpoint-usage-example` previously cloned

5. Provide the workspace<br/>
copy the workspace to the data folder so that the mets is available at data/mets.xml

6. Run a workflow
```
curl -v -X POST "localhost:8080/workflow?workspace_path=/data/mets.xml" -H "Content-type: multipart/form-data" -F "workflow=@test-workflow.txt"
```

