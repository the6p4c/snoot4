import os
from pathlib import Path
import subprocess
from subprocess import CalledProcessError
import sys
import tempfile
import textwrap


def main():
    if len(sys.argv) != 2:
        print(f"error: must provide assembly as first command line argument")
        print()
        print(f"usage:")
        print(f"    pdm assemble <assembly code>")
        sys.exit(1)

    path_as = os.environ.get("AS", "sh4-elf-as")
    path_objdump = os.environ.get("OBJDUMP", "sh4-elf-objdump")
    asm = sys.argv[1]

    with tempfile.NamedTemporaryFile(suffix=".o", delete=False) as file_elf:
        try:
            cmd = [path_as, "--isa=sh4", "-o", file_elf.name]
            subprocess.run(cmd, input=f"{asm}\n", text="utf-8", check=True)

            cmd = [path_objdump, "-d", file_elf.name]
            process = subprocess.run(cmd, capture_output=True, text="utf-8", check=True)
        except CalledProcessError:
            sys.exit(1)
        finally:
            Path(file_elf.name).unlink(missing_ok=True)

        objdump_stdout = process.stdout

    HEADER = "00000000 <.text>:\n"
    start = objdump_stdout.index(HEADER) + len(HEADER)
    assembled = textwrap.dedent(objdump_stdout[start:].rstrip())

    print(assembled)


if __name__ == "__main__":
    main()
