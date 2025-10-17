from dataclasses import dataclass

from grabit_lib.core.output_format import OutputFormatList


@dataclass
class RenderFlags:
    include_source: bool
    include_title: bool
    yaml_frontmatter: bool


@dataclass
class OutputFlags:
    output_formats: OutputFormatList
    create_domain_subdir: bool
    overwrite: bool
