import click

from grabit_md import Grabber, GrabitError, OutputFormat, __version__


@click.command()
@click.argument("url")
@click.option(
    "--user-agent",
    default=f"Grabit/{__version__}",
    help="The user agent reported when retrieving web pages",
    show_default=True,
)
@click.version_option(
    version=__version__,
    prog_name="Grabit",
    message="%(prog)s v%(version)s © 2025 Vlad Iliescu\n%(prog)s is licensed under the LGPL v3 License (https://www.gnu.org/licenses/lgpl-3.0.html)",
)
@click.option(
    "--yaml-frontmatter/--no-yaml-frontmatter",
    default=True,
    help="Include YAML front matter with metadata.",
    show_default=True,
)
@click.option(
    "--include-title/--no-include-title",
    default=True,
    help="Include the page title as an H1 heading.",
    show_default=True,
)
@click.option(
    "--include-source/--no-include-source",
    default=False,
    help="Include the page source.",
    show_default=True,
)
@click.option(
    "--fallback-title",
    default="Untitled {date}",
    help="Fallback title if no title is found. Use {date} for current date.",
    show_default=True,
)
@click.option(
    "--use-readability-js/--no-use-readability-js",
    default=True,
    help="Use Readability.js for processing pages, requires Node to be installed (recommended).",
    show_default=True,
)
@click.option(
    "--create-domain-subdir/--no-create-domain-subdir",
    default=True,
    help="Save the resulting file(s) in a subdirectory named after the domain.",
    show_default=True,
)
@click.option(
    "--overwrite/--no-overwrite",
    default=False,
    help="Overwrite existing files if they already exist.",
    show_default=True,
)
@click.option(
    "-f",
    "--format",
    "output_formats",
    multiple=True,
    default=[OutputFormat.MD.value],
    type=click.Choice([fmt.value for fmt in OutputFormat], case_sensitive=False),
    help="Which output format(s) to use when saving the content. Can be specified multiple times i.e. -f md -f html",
    show_default=True,
)
def main(
    url: str,
    user_agent: str,
    use_readability_js: bool,
    yaml_frontmatter: bool,
    include_title: bool,
    include_source: bool,
    fallback_title: str,
    create_domain_subdir: bool,
    output_formats: list[str],
    overwrite: bool,
) -> None:
    """
    Download a URL, convert it to Markdown/HTML with specified options, and save it to a file.
    """
    try:
        grabber = Grabber(user_agent=user_agent)
        grabber.grab_and_save(
            url=url,
            use_readability_js=use_readability_js,
            fallback_title=fallback_title,
            include_source=include_source,
            include_title=include_title,
            yaml_frontmatter=yaml_frontmatter,
            output_formats=list(output_formats),
            create_domain_subdir=create_domain_subdir,
            overwrite=overwrite,
        )
    except GrabitError as e:
        raise click.ClickException(str(e))


if __name__ == "__main__":
    main()
