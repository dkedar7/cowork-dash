"""The README's config-priority chain must name every TOML layer core reads (gh #128).

The Configuration section — the one section entirely about ``langstage.toml`` — first
stated the priority as *"Python args > CLI args > environment variables > defaults"*,
dropping TOML entirely (gh #100); it was then fixed to a single ``langstage.toml`` layer.
But ``langstage-core``'s resolver actually reads **two** TOML layers: the global
``~/.langstage/config.toml`` (dir overridable via ``LANGSTAGE_CONFIG_HOME``) and the
project ``langstage.toml`` discovered by walking *up* from cwd, with the project file
winning. This pins the README to that real chain and to the global-layer docs (gh #128).
"""
from pathlib import Path

from langstage.cli import main as cli_main
from langstage.config_template import _HEADER

from click.testing import CliRunner

_README = Path(__file__).resolve().parent.parent / "README.md"


def test_priority_line_names_both_toml_layers_between_env_and_defaults():
    text = _README.read_text(encoding="utf-8")
    # The corrected chain: project langstage.toml, then global config.toml, then defaults.
    assert (
        "environment variables > project `langstage.toml` (nearest at or above the "
        "working directory) > global `~/.langstage/config.toml` > defaults"
    ) in text
    # The earlier three-layer statement that silently dropped TOML is gone (gh #100)...
    assert "environment variables > defaults" not in text
    # ...and so is the single-layer chain that omitted the global file (gh #128).
    assert "environment variables > `langstage.toml` > defaults" not in text


def test_readme_documents_the_global_layer_and_config_home():
    """The global config file and its env override must be documented (gh #128)."""
    text = _README.read_text(encoding="utf-8")
    assert "~/.langstage/config.toml" in text
    assert "LANGSTAGE_CONFIG_HOME" in text
    # The upward-walk discovery is what makes a parent-directory file surprising.
    assert "walking **up**" in text


def test_readme_agrees_with_init_header_and_show_config():
    """All three surfaces name the TOML layer, so they can't contradict each other."""
    readme = _README.read_text(encoding="utf-8")
    assert "langstage.toml" in readme.lower()

    # The init-generated header names "this file" (the langstage.toml) in the chain.
    assert "this file > defaults" in _HEADER

    # --show-config help spells the chain low-to-high and includes langstage.toml.
    help_out = CliRunner().invoke(cli_main, ["--help"]).output
    assert "langstage.toml" in help_out
