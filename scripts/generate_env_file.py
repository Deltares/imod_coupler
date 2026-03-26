import argparse
from pathlib import Path

import jinja2


def generate_env_file(exec: str) -> None:
    template_generator = jinja2.Environment(
        loader=jinja2.FileSystemLoader("scripts/templates"),
        autoescape=True,
    )
    template = template_generator.get_template(".env.jinja")
    with open(".env", "w") as f:
        f.write(
            template.render(
                imod_coupler_exec=exec,
                imod_collector_dev_path=Path("./.imod_collector/develop").resolve(),
                imod_collector_regression_path=Path(
                    "./.imod_collector/regression"
                ).resolve(),
                metaswap_lookup_table_path=Path(
                    "./.imod_collector/LHM2016_v01vrz"
                ).resolve(),
            )
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate the .env file for imod_coupler."
    )
    parser.add_argument(
        "imodc",
        nargs="?",
        default="local",
        help="Path or name of the imodc executable (default: 'local' to use the local Python code)",
    )
    args = parser.parse_args()
    generate_env_file(args.imodc)
