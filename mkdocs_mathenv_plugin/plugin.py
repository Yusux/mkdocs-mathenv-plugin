import os
import re

from mkdocs.plugins import BasePlugin
from mkdocs.structure.pages import Page
from mkdocs.structure.files import Files
from mkdocs.config.defaults import MkDocsConfig
from mkdocs.config import base, config_options, Config
from mkdocs.utils import log, copy_file

from typing import Optional, Dict, Any

from .tikz import TikZObject
from .markdown_utils import replace_standalone_words, replace_indented_block_start_with_options, get_indentation_level, return_to_indentation_level

PLUGIN_DIR = os.path.dirname(os.path.realpath(__file__))

def append(origin, new):
    """
    Append new to origin, if origin is None, return new
    """
    if origin is None:
        return new
    else:
        return origin + new

class _TheoremOptions(base.Config):
    enable = config_options.Type(bool, default=False)
    theorem = config_options.Type(str, default="定理")
    lemma = config_options.Type(str, default="引理")
    proposition = config_options.Type(str, default="命题")
    definition = config_options.Type(str, default="定义")
    proof = config_options.Type(str, default="证明")
    exercise = config_options.Type(str, default="习题")

class _TikZcdOptions(base.Config):
    enable = config_options.Type(bool, default=False)
    cachefile = config_options.Type(bool, default=True)

class _TikZpictureOptions(base.Config):
    enable = config_options.Type(bool, default=False)
    cachefile = config_options.Type(bool, default=True)

class _AliasOptions(base.Config):
    enable = config_options.Type(bool, default=False)
    alias_list = config_options.Type(Dict, default={})

class MathEnvConfig(base.Config):
    theorem = config_options.SubConfig(_TheoremOptions)
    tikzcd = config_options.SubConfig(_TikZcdOptions)
    tikzpicture = config_options.SubConfig(_TikZpictureOptions)
    alias = config_options.SubConfig(_AliasOptions)

class MathEnvPlugin(BasePlugin[MathEnvConfig]):

    def on_config(self, config: MkDocsConfig) -> Optional[Config]:
        config["extra_css"] = ["css/svg.css"] + config["extra_css"]

    def on_pre_build(self, *, config: MkDocsConfig) -> None:
        """
        Just for debugging
        """
        if self.config.theorem.enable:
            log.debug("[mathenv] theorem environment enabled!")
            log.debug("[mathenv] theorem titled with %s" % self.config.theorem.theorem)
            log.debug("[mathenv] lemma titled with %s" % self.config.theorem.lemma)
            log.debug("[mathenv] proposition titled with %s" % self.config.theorem.proposition)
            log.debug("[mathenv] definition titled with %s" % self.config.theorem.definition)
            log.debug("[mathenv] proof replaced with %s" % self.config.theorem.proof)

        if self.config.tikzcd.enable:
            log.debug("[mathenv] tikzcd enabled!")
        if self.config.tikzcd.cachefile:
            log.debug("[mathenv] cache file enabled!")
            if not os.path.exists("cache"):
                os.mkdir("cache")
                log.debug("[mathenv] created path cache/")
        
        if self.config.alias.enable:
            log.debug("[mathenv] alias enabled!")
            log.debug(f"[mathenv] current alias list: {self.config.alias.alias_list}")
        
        return config

    def on_page_markdown(self, markdown: str, *, page: Page, config: MkDocsConfig, files: Files) -> Optional[str]:
        """
        On markdown, extend the theorem expression
        """
        def _replace_tikz(matched: re.Match[str]) -> str:
            """
            For each matched string, clean the first line label and transform it into html script 
            """
            leading = matched.group("leading")
            command = matched.group("command")
            mode = matched.group("mode")
            options = matched.group("options")
            contents = matched.group("contents")
            first_line_indentation_level = get_indentation_level(matched.group("contents"))

            log.debug(first_line_indentation_level)

            if mode == "automata":
                options = append(options, r'->,>={Stealth[round]},shorten >=1pt,auto,node distance=2cm,on grid,semithick,inner sep=2pt,bend angle=50,initial text=')

            contents = [i for i in contents.splitlines()]

            contents_remain = []

            for idx, i in enumerate(contents):
                if get_indentation_level(i) < first_line_indentation_level:
                    contents_remain = contents[idx:]
                    contents = contents[:idx]
                    break

            contents = "\n".join(contents)
            tikzcd = TikZObject(command, options, contents)

            # The string should not be splitted into lines, since markdown parser won't recognize it
            svg_str = "".join(tikzcd.write_to_svg(self.config.tikzcd.cachefile).removeprefix("<?xml version='1.0' encoding='UTF-8'?>\n").splitlines())

            return f"{leading}<div class=tikzcd-svg align=center>{svg_str}</div>" + "\n" + "\n".join(contents_remain)

        if self.config.theorem.enable:
            markdown = re.sub(r"(?<!\\)\\theorem", "!!! success \"%s\"" % self.config.theorem.theorem, markdown)
            # fix possible use of "\theorem" when you don't need it
            markdown = re.sub(r"\\\\theorem", r"\\theorem", markdown)
            markdown = re.sub(r"(?<!\\)\\lemma", "!!! success \"%s\"" % self.config.theorem.lemma, markdown)
            markdown = re.sub(r"\\\\lemma", r"\\lemma", markdown)
            markdown = re.sub(r"(?<!\\)\\proposition", "!!! success \"%s\"" % self.config.theorem.proposition, markdown)
            markdown = re.sub(r"\\\\proposition", r"\\proposition", markdown)
            markdown = re.sub(r"(?<!\\)\\definition", "!!! info \"%s\"" % self.config.theorem.definition, markdown)
            markdown = re.sub(r"\\\\definition", r"\\definition", markdown)
            markdown = re.sub(r"(?<!\\)\\proof", "???+ info \"%s\"" % self.config.theorem.proof, markdown)
            markdown = re.sub(r"\\\\proof", r"\\proof", markdown)
            markdown = re.sub(r"(?<!\\)\\exercise", "!!! question \"%s\"" % self.config.theorem.exercise, markdown)
            markdown = re.sub(r"\\\\exercise", r"\\exercise", markdown)

        if self.config.tikzcd.enable:
            markdown = replace_indented_block_start_with_options(r"(?<!\\)\\tikzcd", _replace_tikz, markdown)
            markdown = re.sub(r"\\\\tikzcd", r"\\tikzcd", markdown)

        if self.config.tikzpicture.enable:
            markdown = replace_indented_block_start_with_options(r"(?<!\\)\\tikzpicture", _replace_tikz, markdown)
            markdown = re.sub(r"\\\\tikzpicture", r"\\tikzpicture", markdown)

        log.debug(f"markdown file: \n{markdown}")

        return markdown

    def on_page_content(self, html: str, *, page: Page, config: MkDocsConfig, files: Files) -> Optional[str]:
        """
        On each page, find the environment to replace and generate something
        """

    def on_post_build(self, config: Dict[str, Any], **kwargs) -> None:
        """
        Add svg stylesheet support
        """ 
        files = ["css/svg.css"]
        for file in files:
            dest_file_path = os.path.join(config["site_dir"], file)
            src_file_path = os.path.join(PLUGIN_DIR, file)
            log.debug(f"loading svg: {src_file_path}")
            assert os.path.exists(src_file_path)
            copy_file(src_file_path, dest_file_path)