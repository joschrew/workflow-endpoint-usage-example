#!/usr/bin/env python
""" Script to create the docker-compose file for running the conainers for the workflow-endpoint

For the example run the processing server is started via CMD. It needs mongoDB, rabbitMQ and the
workers. These are run with the docker-compose.yaml created with this script
"""

import requests
from pathlib import Path
import yaml
import re
import sys

DEST_ENV = "../.env"
# Purpose was to change the image of containers for debugging. Left here as reminder if needed again
IMAGE_NAME = ""

CONFIG_PATH = "configs/default.yaml" if len(sys.argv) == 1 else sys.argv[1]
assert Path(CONFIG_PATH).exists(), f"specified config file not existing: '{sys.argv[1]}'"

with open(CONFIG_PATH) as fin:
    config = yaml.safe_load(fin)

assert isinstance(config, dict), (
    "error reading config-file to dict. Expecting dict but is "
    f"{type(config)}"
)
DEST = config["dest"]
BASE_TEMPLATE = config["dc_base_template"]
SERVICE_TEMPLATE = config["dc_service_template"]
USE_CUSTOM_LOGGING_CONF = config.get("use_custom_logging_config", False)
TESSERACT_VOL_REPLACEMENT = config.get("tesseract_vol_replacement", None)
TESSDATA_PREFIX = config.get("tessdata_prefix", None)

# processors from ocrd-all-tool-json to be skipped
# they are present in the ocrd-tool-json but matching binaries are not available in ocrd_all. Maybe
# they are misspelled in the ocrd-all-tool.json or no longer available in ocrd_all
BLOCK_LIST = [
    "ocrd-cor-asv-fst-process",
    "ocrd-dummy",
    "ocrd-pc-segmentation",
    "ocrd-ocropy-segment",
    "ocrd-page2tei",
    "ocrd-sbb-textline-detector",
    "ocrd-cis-ocropy-rec",
]

# If at least one processor specified, don't create all workers just these ones
ALLOW_LIST = config["processors"]


def write_docker_compose(dirname, data):
    base = Path(__file__).resolve().parent.parent
    path = base.joinpath(dirname).joinpath("docker-compose.yaml")
    with open(path, "w") as fout:
        yaml.dump(data, fout, default_style=False)


def get_processors():
    r = requests.get("https://ocr-d.de/js/ocrd-all-tool.json")
    processors = r.json().keys()
    if len(ALLOW_LIST) > 0:
        assert all(used_proc in processors for used_proc in ALLOW_LIST), (
            f"Processor-name in config (key: 'processors') not valid. "
            f"Invalid: '{[p for p in ALLOW_LIST if not p in processors]}'"
        )
        return ALLOW_LIST
    else:
        res = [x for x in processors if x not in BLOCK_LIST]
        res.sort()
        return res


def dc_head() -> str:
    with open(BASE_TEMPLATE, "r") as fin:
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

        # add Fraktur models for tesseract recognize
        if TESSERACT_VOL_REPLACEMENT \
                and p in ["ocrd-tesserocr-recognize", "ocrd-tesserocr-segment-region"]:
            template_for_processor = re.sub(
                r"    volumes:",
                f"    {TESSERACT_VOL_REPLACEMENT}",
                template_for_processor,
            )

        # optionally replace `image: ...` with for example `build:\ncontext: path/Dockerfile`
        if isinstance(processors, dict) and processors[p]:
            template_for_processor = re.sub(
                r"image: [\S]+[\n]", processors[p], template_for_processor
            )

        # optionally set custom logging conf through volume mount
        if USE_CUSTOM_LOGGING_CONF and p.find("tesser") > -1:
            assert Path("../my_ocrd_logging.conf").exists(), "custom logging conf not found"
            template_for_processor = re.sub(
                r"    volumes:",
                '    volumes:\n      - "./my_ocrd_logging.conf:/root/ocrd_logging.conf"',
                template_for_processor,
            )

        # optionally add environment Variable for tesseract Images:
        if p.startswith("ocrd-tesserocr-") and TESSDATA_PREFIX:
            template_for_processor = re.sub(
                r"    environment:",
                f"    environment:\n      - TESSDATA_PREFIX={TESSDATA_PREFIX}",
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
