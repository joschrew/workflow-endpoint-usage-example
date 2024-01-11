#!/usr/bin/env python
""" Script to create the docker-compose file for running the conainers for the workflow-endpoint

For the example run the processing server is started via CMD. It needs mongoDB, rabbitMQ and the
workers. These are run with the docker-compose.yaml created with this script
"""

import requests
from pathlib import Path
import yaml
import re

DEST = "../docker-compose.yaml"
DEST_ENV = "../.env"
# Purpose is to change the image of containers for debugging. Left here as reminder if needed again
IMAGE_NAME = ""


DC_BASE_TEMPLATE = "docker-compose.template.yaml"
SERVICE_TEMPLATE = "docker-compose.processor.template.yaml"

PROCESSORS_CUSTOM = "use_processors.yaml"

USE_CUSTOM_LOGGING_CONF = True

# processors from ocrd-all-tool-json to be skipped
# they are present in the ocrd-tool-json but matching binaries are not available in ocrd_all. Maybe
# they are misspelled in the ocrd-all-tool.json or no longer available in ocrd_all
BLOCK_LIST = [
    "ocrd-cor-asv-fst-process",
    "ocrd-pc-segmentation",
    "ocrd-ocropy-segment",
    "ocrd-page2tei",
    "ocrd-sbb-textline-detector",
    "ocrd-cis-ocropy-rec",
]

FRAKTUR_VOL_REPLACEMENT = (
    '"$PWD/Fraktur.traineddata:/models/ocrd-tesserocr-recognize/Fraktur.traineddata"'
)

# list read from PROCESSORS_CUSTOM to only create specific processors and not all
ALLOW_LIST = []
if Path(PROCESSORS_CUSTOM).exists():
    with open(PROCESSORS_CUSTOM) as fin:
        ALLOW_LIST = yaml.safe_load(fin)


def write_docker_compose(dirname, data):
    base = Path(__file__).resolve().parent.parent
    path = base.joinpath(dirname).joinpath("docker-compose.yaml")
    with open(path, "w") as fout:
        yaml.dump(data, fout, default_style=False)


def get_processors():
    r = requests.get("https://ocr-d.de/js/ocrd-all-tool.json")
    processors = r.json().keys()
    if len(ALLOW_LIST) > 0:
        assert all(used_proc in processors for used_proc in ALLOW_LIST), \
            f"Processor-name in {PROCESSORS_CUSTOM} not valid"
        return ALLOW_LIST
    else:
        return [x for x in processors if x not in BLOCK_LIST]


def dc_head() -> str:
    with open(DC_BASE_TEMPLATE, "r") as fin:
        return fin.read()


def dc_workers() -> str:
    res = ""
    processors = get_processors()
    with open(SERVICE_TEMPLATE, "r") as fin:
        template = fin.read()
    if IMAGE_NAME:
        template = template.replace("ocrd/all:maximum", IMAGE_NAME)

    for p in processors:
        template_for_processor = re.sub(r"{{[\s]*processor_name[\s]*}}", p, template)
        if p == "ocrd-tesserocr-recognize":
            template_for_processor = re.sub(
                r"    volumes:",
                f"    volumes:\n      - {FRAKTUR_VOL_REPLACEMENT}",
                template_for_processor,
            )
        # optionally replace `image: ...` with for example `build:\ncontext: path/Dockerfile`
        if isinstance(processors, dict) and processors[p]:
            template_for_processor = re.sub(
                r"image: [\S]+[\n]", processors[p], template_for_processor
            )

        # optionally set custom logging conf through volume mount
        if USE_CUSTOM_LOGGING_CONF:
            assert Path("../my_ocrd_logging.conf").exists(), "custom logging conf not found"
            template_for_processor = re.sub(
                r"    volumes:",
                "    volumes:\n      - \"./my_ocrd_logging.conf:/etc/ocrd_logging.conf\"",
                template_for_processor,
            )

        res += template_for_processor

    return res


def main():
    if not Path(DEST_ENV).exists():
        lines = [
            "OCRD_PS_PORT=8000",
            "OCRD_PS_MTU=1300",
            "MONGODB_USER=admin",
            "MONGODB_PASS=admin",
            "MONGODB_URL=mongodb://${MONGODB_USER}:${MONGODB_PASS}@ocrd-mongodb:27017",
            "RABBITMQ_USER=admin",
            "RABBITMQ_PASS=admin",
            "RABBITMQ_URL=amqp://${RABBITMQ_USER}:${RABBITMQ_PASS}@ocrd-rabbitmq:5672",
            "USER_ID=1000",
            "GROUP_ID=1000",
            "DATA_DIR_HOST=${PWD}/data"
        ]
        with open(DEST_ENV, "w+") as fout:
            fout.write("\n".join(lines))
    else:
        print("Skipping writing to .env")

    with open(DEST, "w") as fout:
        header = dc_head()
        if IMAGE_NAME:
            header = dc_head().replace("ocrd/all:maximum", IMAGE_NAME)

        fout.write(header)
        fout.write(dc_workers())


if __name__ == "__main__":
    main()
