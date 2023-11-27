# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
#
# SPDX-License-Identifier: MIT-0
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this
# software and associated documentation files (the "Software"), to deal in the Software
# without restriction, including without limitation the rights to use, copy, modify,
# merge, publish, distribute, sublicense, and/or sell copies of the Software, and to
# permit persons to whom the Software is furnished to do so.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
# INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A
# PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION
# OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE
# SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.


from pathlib import Path
from typing import List
from zipfile import ZipFile
import os


class ZipUtility:
    base_dir: str = os.path.abspath(f'{os.path.dirname(__file__)}{os.path.sep}..{os.path.sep}..')

    @classmethod
    def create_zip(cls, local_paths: [str, List[str]], out_path: Path = Path(".zip_archives")):
        """
        Create a zip archive with the content of `local_path`
        :param local_paths: The path to the directory to zip
        :param out_path: The path to the output zip file The file name is created from
        the local path one
        """

        base_paths: List[str] = [local_paths] if isinstance(local_paths, str) else local_paths
        first_base_dir: Path = Path(base_paths[0])

        out_path.mkdir(exist_ok=True)
        local_sub_path = "_".join(str(first_base_dir.absolute()).split(os.path.sep)[-4:])
        out_path = out_path / f"{local_sub_path}.zip"

        with ZipFile(out_path, mode="w") as archive:
            for local_path in map(lambda p: Path(p), base_paths):
                [
                    archive.write(k, arcname=f"{k.relative_to(local_path)}")
                    for k in local_path.glob("**/*")
                    if not f"{k.relative_to(local_path)}".startswith((os.getenv('CDK_OUTDIR', "cdk.out")))
                    if "__pycache__" not in f"{k.relative_to(local_path)}"
                    if not f"{k.relative_to(local_path)}".endswith(".zip")
                ]

        return f"{out_path}"
