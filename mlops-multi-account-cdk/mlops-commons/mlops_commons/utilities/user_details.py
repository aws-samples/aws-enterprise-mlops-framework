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


class UserDetails:

    @classmethod
    def get_secondary_owner_by_user(cls, user: str) -> str:

        cmd = f'curl https://phonetool.amazon.com/users/{user}/setup_org_chart.json' \
              f' -L -s  --cookie {os.environ["HOME"]}/.midway/cookie'

        res: str = cls.run(cmd=cmd, user=user)
        org = json.loads(res)

        user_level: int = list(filter(lambda x: x['username'] == user, org['results']))[0]['level']
        secondary_owner: str = list(filter(lambda x: x['level'] == user_level - 1, org['results']))[0]['username']

        return secondary_owner

    @staticmethod
    def run(cmd: str, user: str) -> str:

        process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, shell=True, text=True)
        res: str = ""
        num_empty_lines = 0
        while True:
            line = process.stdout.readline().rstrip()
            if not line and num_empty_lines > 5 or '<!DOCTYPE html>' in line:
                if '<!DOCTYPE html>' in line:
                    raise Exception(f"User : {user}, doesn't exist")
                break
            res = f'{res}{line}'
            num_empty_lines = num_empty_lines + 1
        process.kill()

        return res


# used for shell script to get attribute value
if __name__ == '__main__':
    print(UserDetails.get_secondary_owner_by_user(sys.argv[1]))
