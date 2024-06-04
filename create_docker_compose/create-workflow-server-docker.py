#!/usr/bin/env python
""" Script to create the docker-compose file for running the conainers for the workflow-endpoint

"""

import requests
from pathlib import Path
import yaml
import re
import click

DEST_ENV = "../.env"
# Purpose was to change the image of containers for debugging. Left here as reminder if needed again
IMAGE_NAME = ""


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


class Config:
    def __init__(self, config_path=None):
        # TODO: automatically convert the yaml to a class and skip most of this stuff
        if not config_path:
            self.config_path = "configs/default.yaml"
        else:
            self.config_path = config_path
        assert Path(self.config_path).exists(), (
            f"specified config file not existing: '{self.config_path}'"
        )

        with open(self.config_path) as fin:
            config = yaml.safe_load(fin)

        assert isinstance(config, dict), (
            "error reading config-file to dict. Expecting dict but is "
            f"{type(config)}"
        )
        self.dest = config["dest"]
        self.dest_env = config.get("dest_env", DEST_ENV)
        self.base_template = config["dc_base_template"]
        self.service_template = config["dc_service_template"]
        self.vol_replacement = config.get("vol_replacement", None)
        self.tessdata_prefix = config.get("tessdata_prefix", None)
        # If at least one processor specified, don't create all workers just these ones
        self.allow_list = config["processors"]
        self.envs = config.get("envs", [])
        self.always_write_env = config.get("always_write_env", False)


def write_docker_compose(dirname, data):
    base = Path(__file__).resolve().parent.parent
    path = base.joinpath(dirname).joinpath("docker-compose.yaml")
    with open(path, "w") as fout:
        yaml.dump(data, fout, default_style=False)


def get_processors(config: Config):
    r = requests.get("https://ocr-d.de/js/ocrd-all-tool.json")
    processors = r.json().keys()
    if len(config.allow_list) > 0:
        assert all(used_proc in processors for used_proc in config.allow_list), (
            f"Processor-name in config (key: 'processors') not valid. "
            f"Invalid: '{[p for p in config.allow_list if not p in processors]}'"
        )
        return config.allow_list
    else:
        res = [x for x in processors if x not in BLOCK_LIST]
        res.sort()
        return res


def dc_head(config: Config) -> str:
    with open(config.base_template, "r") as fin:
        return fin.read()


def dc_workers(config: Config) -> str:
    res = ""
    processors = get_processors(config)
    with open(config.service_template, "r") as fin:
        template = fin.read()
    if IMAGE_NAME:
        template = template.replace("ocrd/all:maximum", IMAGE_NAME)

    for p in processors:
        template_for_processor = re.sub(r"{{[\s]*processor_name[\s]*}}", p, template)

        # add volume mounts for some containers
        if config.vol_replacement and p in config.vol_replacement:
            template_for_processor = re.sub(
                r"    volumes:",
                f"    {config.vol_replacement[p]}",
                template_for_processor,
            )

        # optionally replace `image: ...` with for example `build:\ncontext: path/Dockerfile`
        if isinstance(processors, dict) and processors[p]:
            template_for_processor = re.sub(
                r"image: [\S]+[\n]", processors[p], template_for_processor
            )

        # optionally add environment Variable for tesseract Images:
        if p.startswith("ocrd-tesserocr-") and config.tessdata_prefix:
            template_for_processor = re.sub(
                r"    environment:",
                f"    environment:\n      - TESSDATA_PREFIX={config.tessdata_prefix}",
                template_for_processor,
            )

        res += template_for_processor

    return res


@click.command()
@click.argument("config_path")
def main(config_path):
    config = Config(config_path)
    if config.always_write_env or not Path(config.dest_env).exists():
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
            "DATA_DIR_HOST=${PWD}/data",
        ]
        # overwrite default envs
        for env in config.envs:
            varname = env.split("=")[0]
            r = re.compile(f"{varname}=.*")
            matches = list(filter(r.match, lines))
            assert not len(matches) > 1, "error replacing env. duplicate env or programmer mistake"
            if len(matches) == 1:
                lines[lines.index(matches[0])] = env
            else:
                lines.append(env)

        with open(config.dest_env, "w+") as fout:
            fout.write("\n".join(lines))
    else:
        print("Skipping writing to .env")

    with open(config.dest, "w") as fout:
        header = dc_head(config)
        if IMAGE_NAME:
            header = dc_head(config).replace("ocrd/all:maximum", IMAGE_NAME)

        fout.write(header)
        fout.write(dc_workers(config))


if __name__ == "__main__":
    main()
