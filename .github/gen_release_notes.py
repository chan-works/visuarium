import subprocess
import datetime
import os
import sys

date = datetime.datetime.now().strftime("%Y.%m.%d")
run = sys.argv[1] if len(sys.argv) > 1 else "0"
tag = f"v{date}-{run}"

# Write tag to GITHUB_OUTPUT
github_output = os.environ.get("GITHUB_OUTPUT", "")
if github_output:
    with open(github_output, "a", encoding="utf-8") as f:
        f.write(f"tag={tag}\n")

# Get recent commit messages
try:
    logs = subprocess.check_output(
        ["git", "log", "--pretty=format:- %s", "-10"],
        encoding="utf-8", errors="replace"
    )
except Exception:
    logs = "- (커밋 정보를 가져올 수 없습니다)"

body = (
    "## 다운로드\n"
    "agent_Windows.zip 받아서 압축 해제 후 agent.exe 실행\n\n"
    "## 첫 실행 방법\n"
    "1. ZIP 압축 해제\n"
    "2. agent.exe 실행\n"
    "3. 설정 탭 -> Claude API Key 입력 -> 저장\n"
    "4. 세션 탭 -> 세션 시작\n\n"
    "---\n"
    "## 수정사항\n"
    f"{logs}\n"
)

with open("release_body.txt", "w", encoding="utf-8") as f:
    f.write(body)

print(f"Generated release notes for {tag}")
