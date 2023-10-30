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
from base64 import b64decode
from base64 import b64encode
from typing import List, Dict, Any, Optional

import yaml


class YamlHelper(object):

    @staticmethod
    def merge_yaml_files(yaml_file_paths: List[str], output_file_path: str) -> None:
        merged_yaml = YamlHelper.merge_files(yaml_file_paths)
        YamlHelper.write_yaml(merged_yaml, output_file_path)

    @staticmethod
    def merge_yaml(yaml_file_paths: List[str]) -> str:
        merged_yaml = YamlHelper.merge_files(yaml_file_paths)
        return yaml.dump(merged_yaml)

    @classmethod
    def load_yaml(cls, yaml_file_path) -> Dict[str, Any]:
        with open(yaml_file_path, 'r') as stream: return yaml.safe_load(stream);

    @classmethod
    def merge_files(cls, yaml_file_paths) -> Dict[str, Any]:
        merged_yaml: Optional[Dict[str, Any]] = None
        for yaml_file_path in yaml_file_paths:
            if merged_yaml is None:
                merged_yaml = YamlHelper.load_yaml(yaml_file_path)
            else:
                for k, v in YamlHelper.load_yaml(yaml_file_path).items():
                    if k == 'RulesToSuppress':
                        for e in v:
                            merged_yaml['RulesToSuppress'].append(e)
        return merged_yaml

    @classmethod
    def write_yaml(cls, merged_yaml, output_file_path):
        with open(output_file_path, 'w') as outfile:
            yaml.dump(merged_yaml, outfile, default_flow_style=False)
        return output_file_path

    @classmethod
    def encode_file_as_base64_string(cls, file_path: str) -> str:
        with open(file_path, 'r') as file:
            return b64encode(bytes(file.read(), 'utf-8')).decode('utf-8')

    @classmethod
    def decode_base64_string(cls, base64_string: str) -> str:
        return b64decode(base64_string).decode('utf-8')

    @classmethod
    def merge_yaml_file_with_base64_string(cls, yaml_file_path: str, yaml_file_base64_string: str) -> str:
        mandatory_yml = cls.decode_base64_string(yaml_file_base64_string)
        m_yml = yaml.safe_load(mandatory_yml)

        for k, v in cls.load_yaml(yaml_file_path).items():
            if k == 'RulesToSuppress':
                for e in v:
                    m_yml['RulesToSuppress'].append(e)
        return yaml.dump(m_yml)
