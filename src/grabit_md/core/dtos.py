from dataclasses import dataclass


@dataclass
class RenderFlags:
    include_source: bool
    include_title: bool
    yaml_frontmatter: bool


@dataclass
class OutputFlags:
    create_domain_subdir: bool
    overwrite: bool
