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

import json
import os
import subprocess
import sys
from typing import List, Any


class IsenAccountUtils:

    @classmethod
    def configure_aws_profile(cls, stage: str, account: str, role: str = 'Admin', profile_name: str = None) -> str:
        profile: str = f'{os.environ["USER"]}_{account}_{stage}_{role}' if profile_name is None else profile_name
        credentials = cls.get_temporary_credentials(account=account, role=role)
        cls.create_profile(access_key=credentials.get('accessKeyId'),
                           secret_key=credentials.get('secretAccessKey'),
                           session_token=credentials.get('sessionToken'),
                           profile_name=profile)
        return profile

    @classmethod
    def get_temporary_credentials(cls, account: str, role: str) -> Any:

        post_payload = json.dumps({"AWSAccountID": account, "IAMRoleName": role}).replace('"', '\\"')

        cmd = f'curl --cookie ~/.midway/cookie -L -s -X POST ' \
              f'--header "X-Amz-Target: IsengardService.GetAssumeRoleCredentials" ' \
              r'--header "Content-Encoding: amz-1.0" ' \
              r'--header "Content-Type: application/json; charset=UTF-8" ' \
              f'-d "{post_payload}" https://isengard-service.amazon.com'

        res: str = cls.run(cmd=cmd, account=account)
        cred = json.loads(json.loads(res)['AssumeRoleResult'])
        return cred['credentials']

    @classmethod
    def create_profile(cls, profile_name: str, access_key: str, secret_key: str, session_token: str = None) -> None:
        set_access_key_cmd = f'aws configure ' \
                             f'--profile {profile_name} ' \
                             f'set aws_access_key_id {access_key} '

        set_secret_key_cmd = f'aws configure ' \
                             f'--profile {profile_name} ' \
                             f'set aws_secret_access_key {secret_key} '

        set_session_token_cmd = f'aws configure ' \
                                f'--profile {profile_name} ' \
                                f'set aws_session_token {session_token}'

        cmds: List[str] = list()
        cmds.append(set_access_key_cmd)
        cmds.append(set_secret_key_cmd)
        if set_session_token_cmd is not None and set_session_token_cmd != "":
            cmds.append(set_session_token_cmd)
        for cmd in cmds:
            # print(cmd)
            cls.run(cmd=cmd, account='')

    @staticmethod
    def run(cmd: str, account: str) -> str:
        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, text=True)
        res: str = ""
        num_empty_lines = 0
        while True:
            line = process.stdout.readline().rstrip()
            if not line and num_empty_lines > 5 or 'com.amazon.isengard.coral#AWSAccountNotFoundException' in line:
                if 'com.amazon.isengard.coral#AWSAccountNotFoundException' in line:
                    raise Exception(f"Account : {account}, doesn't exist")
                break
            res = f'{res}{line}'
            num_empty_lines = num_empty_lines + 1
        process.kill()

        return res


# used for shell script to get attribute value
if __name__ == '__main__':
    profile: str = IsenAccountUtils.configure_aws_profile(sys.argv[1], sys.argv[2])
    # print(f'{profile} , created/refreshed Successfully')
    print(profile)
