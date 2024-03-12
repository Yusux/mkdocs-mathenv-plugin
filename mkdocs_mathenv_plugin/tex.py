import os

from mkdocs.utils import log

class TeXError(BaseException):
    pass

class TeXWriterConfig:
    def __init__(self, usepdf: bool=True) -> None:
        self.compiler = "xelatex"
        self.usepdf = usepdf
        self.preamble = ""

class TeXWriter:
    def __init__(self, config=TeXWriterConfig()) -> None:
        self.config = config

    def create_tex_file(self, content: str, tex_name: str) -> None:
        """
        Write content into tex_name, with preamble set by config
        """
        full_tex = "\n\n".join((
            self.config.preamble,
            "\\begin{document}",
            content,
            "\\end{document}"
        )) + "\n"

        try:
            with open(f"{tex_name}.tex", "w", encoding="utf-8") as tex_file:
                tex_file.write(full_tex)
        except OSError:
            log.error("[mathenv] unable to create tex file!")

    def create_svg_from_tex(self, tex_name: str) -> None:
        """
        Generate svg from tex file
        """
        if self.config.compiler == "xelatex":
            program = "xelatex"
            if not self.config.usepdf:
                program += " -no-pdf"
                inter = "xdv"
                dvisvgm_flag = "--no-fonts --font-format=woff2"
            else:
                inter = "pdf"
                dvisvgm_flag = "-P --no-styles --font-format=woff2"
        else:
            raise NotImplementedError(f"Compiler {self.config.compiler} is not implemented!")

        # use compiler to transform tex to intermediate format
        tex2inter_cmd = " ".join((
            program,
            "-halt-on-error",
            "-interaction=batchmode",
            f"\"{tex_name}.tex\"",
            ">",
            os.devnull
        ))

        if os.system(tex2inter_cmd):
            log.error(
                "LaTeX Error! Not a worry, it happens to the best of us."
            )
            raise TeXError("LaTeX Error! Look into log file for detail")

        # use dvisvgm to transform target format to svg
        inter2svg_cmd = " ".join((
            "dvisvgm",
            dvisvgm_flag,
            f"\"{tex_name}.{inter}\"",
            "2>",
            os.devnull
        ))
        log.info(f"running {inter2svg_cmd}")
        if os.system(inter2svg_cmd):
            log.error(
                "dvisvgm Error!"
            )
            raise TeXError("dvisvgm Error!")

        # clean up
        for ext in (".log", ".aux", f".{inter}", ".tex"):
            try:
                os.remove(tex_name + ext)
            except FileNotFoundError:
                pass