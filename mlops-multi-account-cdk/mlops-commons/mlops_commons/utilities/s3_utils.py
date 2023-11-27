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
import logging
from typing import List, Optional, Any

from mlops_commons.utilities.log_helper import LogHelper


class S3Utils:
    logger: logging.Logger = LogHelper.get_logger('S3Utils')

    @classmethod
    def create_bucket_name(cls, name_part1: str, prefix: Optional[str] = None, name_part2: Optional[str] = None,
                           suffix_part1: Optional[str] = None, suffix_part2: Optional[str] = None,
                           prefix_max_len: int = 5,
                           name_part1_max_len: int = 28,
                           name_part2_max_len: int = 9,
                           suffix_part1_max_len: int = 12,
                           suffix_part2_max_len: int = 5,
                           seperator: str = '-',
                           convert_region_to_short_code: bool = True
                           ) -> str:

        if name_part1 is None or name_part1.strip() == "":
            raise ValueError('name_part1 cannot be empty')

        sep: str = cls.sanatize(seperator)
        sep = '-' if sep == '' else sep

        format_string: str = sep.join(['{}' for e in [prefix, name_part1, name_part2, suffix_part1, suffix_part2]
                                       if e is not None and e.strip() != ''])

        cls.logger.info(f'prefix : {prefix}, name_part1 : {name_part1}, '
                        f'name_part2 : {name_part2}, suffix_part1 : {suffix_part1}, suffix_part2 : {suffix_part2},'
                        f' prefix_max_len : {prefix_max_len}, name_part1_max_len : {name_part1_max_len}, '
                        f'name_part2_max_len : {name_part2_max_len}, suffix_part1_max_len : {suffix_part1_max_len}, '
                        f'suffix_part2_max_len : {suffix_part2_max_len}, format_string : {format_string}')

        default_prefix_max_len: int = 5
        default_name_part1_max_len: int = 28
        default_name_part2_max_len: int = 9
        default_suffix_part1_max_len: int = 12
        default_suffix_part2_max_len: int = 5
        # default_region_max_len: int = 13
        # default_region_short_code_max_len: int = 5
        default_seperator_max_len: int = 4
        s3_max: int = 63

        if (
                prefix_max_len
                + name_part1_max_len
                + name_part2_max_len
                + suffix_part1_max_len
                + suffix_part2_max_len
                + default_seperator_max_len
        ) > s3_max:
            raise ValueError(f'Max length of bucket name must be <= {s3_max} characters, please consider adjusting '
                             f'the following parameter(s) : values for parameters constraint '
                             f' prefix_max_len : {prefix_max_len}, name_part1_max_len : {name_part1_max_len}, '
                             f'name_part2_max_len : {name_part2_max_len}, '
                             f'suffix_part1_max_len : {suffix_part1_max_len}, '
                             f'suffix_part2_max_len : {suffix_part2_max_len}')

        # region_len: int = 5 if convert_region_to_short_code else cls.get_max_region_len()
        account_len: int = 12

        prefix_actual_len: int = -1
        name_part1_actual_len: int = -1
        name_part2_actual_len: int = -1
        suffix_part1_actual_len: int = -1
        suffix_part2_actual_len: int = -1

        seperator_actual_len: int = len(sep) * format_string.count(sep)

        if prefix is not None and prefix.strip() != '':
            prefix = cls.sanatize(prefix.lower())
            prefix_actual_len = len(prefix)

        if name_part1 is not None and name_part1.strip() != '':
            name_part1 = cls.sanatize(name_part1.lower())
            name_part1_actual_len = len(name_part1)

        if name_part2 is not None and name_part2.strip() != '':
            name_part2 = cls.sanatize(name_part2.lower())
            name_part2_actual_len = len(name_part2)

        if suffix_part1 is not None and suffix_part1.strip() != '':
            suffix_part1 = cls.sanatize(suffix_part1.lower())
            suffix_part1_actual_len = len(suffix_part1)

        if suffix_part2 is not None and suffix_part2.strip() != '':
            suffix_part2 = cls.sanatize(suffix_part2.lower())
            suffix_part2_actual_len = len(suffix_part2)

        # finding if given args has aws region id
        region_idxs: List[int] = [idx for idx, e in enumerate(
            [prefix, name_part1, name_part2, suffix_part1, suffix_part2]) if e in cls.get_valid_regions()]
        region_idx: int = -1 if len(region_idxs) == 0 else region_idxs[0]

        if convert_region_to_short_code:

            if region_idx != -1:
                if region_idx == 0:
                    prefix = cls.get_region_code(region=prefix)
                    prefix_actual_len = len(prefix)
                elif region_idx == 1:
                    name_part1 = cls.get_region_code(region=name_part1)
                    name_part1_actual_len = len(name_part1)
                elif region_idx == 2:
                    name_part2 = cls.get_region_code(region=name_part2)
                    name_part2_actual_len = len(name_part2)
                elif region_idx == 3:
                    suffix_part1 = cls.get_region_code(region=suffix_part1)
                    suffix_part1_actual_len = len(suffix_part1)
                elif region_idx == 4:
                    suffix_part2 = cls.get_region_code(region=suffix_part2)
                    suffix_part2_actual_len = len(suffix_part2)

        # finding if given args has account id
        account_idxs: List[int] = [idx for idx, e in
                                   enumerate([prefix, name_part1, name_part2, suffix_part1, suffix_part2])
                                   if len(str(e)) == account_len and str(e).isnumeric()]

        account_idx: int = -1 if len(account_idxs) == 0 else account_idxs[0]

        num_chars_to_remove: int = (
                                           default_prefix_max_len
                                           + default_name_part1_max_len
                                           + default_name_part2_max_len
                                           + default_suffix_part1_max_len
                                           + default_suffix_part2_max_len
                                           + default_seperator_max_len
                                   ) - (
                                           prefix_actual_len
                                           + name_part1_actual_len
                                           + name_part2_actual_len
                                           + suffix_part1_actual_len
                                           + suffix_part2_actual_len
                                           + seperator_actual_len
                                   )
        cls.logger.info(
            f'num_chars_to_remove(minus value means remove, plus value means no need to remove) : {num_chars_to_remove}')
        cls.logger.info(
            f'allowed max len : {default_prefix_max_len + default_name_part1_max_len + default_name_part2_max_len + default_suffix_part1_max_len + default_suffix_part2_max_len + default_seperator_max_len}')
        cls.logger.info(
            f'actual len : {prefix_actual_len + name_part1_actual_len + name_part2_actual_len + suffix_part1_actual_len + suffix_part2_actual_len + seperator_actual_len}')
        cls.logger.info(f'checking if given values has aws region, argument position(region_index) : {region_idx}')
        cls.logger.info(f'checking if given values has aws account, argument position(account_index) : {account_idx}')

        if num_chars_to_remove < 0:

            while num_chars_to_remove < 0:
                prev_num_chars_to_remove: int = num_chars_to_remove
                for idx, e in enumerate([prefix, name_part1, name_part2, suffix_part1, suffix_part2]):

                    if idx in [region_idx, account_idx]:
                        continue
                    if idx == 0 and prefix_actual_len > 0 and prefix_max_len > 0:
                        if prefix_max_len < len(prefix):
                            prefix = prefix[:-1]
                            num_chars_to_remove = num_chars_to_remove + 1

                    if idx == 1 and name_part1_actual_len > 0 and name_part1_max_len > 0:
                        if name_part1_max_len < len(name_part1):
                            name_part1 = name_part1[:-1]
                            num_chars_to_remove = num_chars_to_remove + 1

                    if idx == 2 and name_part2_actual_len > 0 and name_part2_max_len > 0:
                        if name_part2_max_len < len(name_part2):
                            name_part2 = name_part2[:-1]
                            num_chars_to_remove = num_chars_to_remove + 1

                    if idx == 3 and suffix_part1_actual_len > 0 and suffix_part1_max_len > 0:
                        if suffix_part1_max_len < len(suffix_part1):
                            suffix_part1 = suffix_part1[:-1]
                            num_chars_to_remove = num_chars_to_remove + 1
                    if idx == 4 and suffix_part2_actual_len > 0 and suffix_part2_max_len > 0:
                        if suffix_part2_max_len < len(suffix_part2):
                            suffix_part2 = suffix_part2[:-1]
                            num_chars_to_remove = num_chars_to_remove + 1
                    if num_chars_to_remove == 0:
                        break
                if prev_num_chars_to_remove == num_chars_to_remove:
                    break
        # https://docs.aws.amazon.com/AmazonS3/latest/dev/BucketRestrictions.html
        # https://docs.aws.amazon.com/AmazonS3/latest/dev/BucketRestrictions.html#bucketnamingrules
        # app_prefix_max_len + project_name_max_len + bucket_type_max_len + acc_id_len + region_max_len == 63

        values: List[Any] = [e for e in [prefix, name_part1, name_part2, suffix_part1, suffix_part2]
                             if e is not None and e.strip() != '']

        return cls.sanatize(format_string.format(*values)[:s3_max])

    @classmethod
    def get_region_code(cls, region: str) -> Optional[str]:
        region = region.lower().strip()
        if region in cls.get_valid_regions():
            return region.replace('east', 'e') \
                .replace('west', 'w') \
                .replace('south', 's') \
                .replace('south', 's') \
                .replace('north', 'n') \
                .replace('central', 'c') \
                .replace('gov', 'g') \
                .replace('-', '')
        return None

    @classmethod
    def get_max_region_len(cls) -> int:
        return max([len(e) for e in cls.get_valid_regions()])

    @staticmethod
    def get_valid_regions() -> List[str]:
        return ['us-east-2', 'us-east-1', 'us-west-1', 'us-west-2', 'af-south-1', 'ap-east-1',
                'ap-south-2', 'ap-southeast-3', 'ap-southeast-4', 'ap-south-1',
                'ap-northeast-3', 'ap-northeast-2', 'ap-southeast-1', 'ap-southeast-2',
                'ap-northeast-1', 'ca-central-1', 'eu-central-1', 'eu-west-1', 'eu-west-2', 'eu-south-1',
                'eu-west-3', 'eu-south-2', 'eu-north-1', 'eu-central-2', 'il-central-1', 'me-south-1',
                'me-central-1', 'sa-east-1', 'us-gov-east-1', 'us-gov-west-1']

    @staticmethod
    def get_allowed_chars() -> List[str]:
        valid_chars: List[str] = ['.', '-']
        for e in range(0, 10):
            valid_chars.append(str(e))
        for e in range(ord('a'), ord('z') + 1):
            valid_chars.append(chr(e))
        return valid_chars

    @classmethod
    def sanatize(cls, token: str) -> str:
        token = token.lower().replace('_', '-').replace('--', '-').replace('..', '.')
        valid_chars: List[str] = cls.get_allowed_chars()
        res: List[str] = [c for c in token if c in valid_chars]
        return ''.join(res)

    @staticmethod
    def sanatize_number(token: str) -> str:
        valid_chars: List[str] = []
        for e in range(0, 10):
            valid_chars.append(str(e))
        res: List[str] = [c for c in token if c in valid_chars]
        return ''.join(res)
