"""진짜 윈도우에서 처음부터 끝까지 — 만든 exe 로 적용하고, 윈도우 도구로 확인하고, 되돌린다.

GitHub 의 윈도우 컴퓨터(관리자 권한)에서 돈다. 이 프로그램의 코드로 확인하면 틀려도 같이
틀리니, 바뀐 값은 윈도우에 원래 들어 있는 reg · powercfg 로 따로 읽는다.

    python tests/windows_e2e.py dist/SuddenAttack-Optimizer.exe

확인 창을 연 모습은 e2e/ 폴더에 화면 사진으로, 전체 기록은 e2e/report.txt 로 남는다.
'참고' 로 표시된 것(창 띄우기·백신·게임 측정)은 GitHub 컴퓨터 환경에 따라 안 될 수 있어서
실패해도 전체를 멈추지는 않는다. 설정을 바꾸고 되돌리는 쪽은 하나라도 틀리면 실패다.
"""

import os
import re
import shutil
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import optimizer as o  # noqa: E402

EXE = str(Path(sys.argv[1]).resolve())
OUT = ROOT / "e2e"
REPORT: list = []
FAILED: list = []
SOFT: list = []

# 30초 동안 색이 계속 바뀌는 창 — 윈도우 화면 합성기(dwm)가 계속 새 장면을 내보내게 한다
ANIMATION = r"""
Add-Type -AssemblyName System.Windows.Forms, System.Drawing
$f = New-Object Windows.Forms.Form
$f.Text = 'animation'; $f.Width = 420; $f.Height = 300; $f.TopMost = $true
$t = New-Object Windows.Forms.Timer; $t.Interval = 15
$script:i = 0
$t.Add_Tick({ $script:i++; $f.BackColor = [Drawing.Color]::FromArgb(($script:i * 7) % 256, ($script:i * 3) % 256, 128) })
$t.Start()
$s = New-Object Windows.Forms.Timer; $s.Interval = 30000; $s.Add_Tick({ $f.Close() }); $s.Start()
[Windows.Forms.Application]::Run($f)
"""


def note(line: str = "") -> None:
    print(line, flush=True)
    REPORT.append(line)


def check(name: str, ok: bool, detail: str = "", soft: bool = False) -> bool:
    mark = "PASS" if ok else ("참고-실패" if soft else "FAIL")
    note(f"{mark:9} {name}{' — ' + detail if detail else ''}")
    if not ok:
        (SOFT if soft else FAILED).append(name)
    return ok


def run(*args: str, timeout: int = 240) -> tuple:
    done = subprocess.run([EXE, *args], capture_output=True, timeout=timeout)
    text = (done.stdout + done.stderr).decode("utf-8", errors="replace")
    note(f"$ {Path(EXE).name} {' '.join(args)}   (끝난 코드 {done.returncode})")
    for line in text.splitlines():
        note("      " + line)
    return done.returncode, text


def shell(*args: str) -> str:
    done = subprocess.run(list(args), capture_output=True)
    return done.stdout.decode("mbcs", errors="replace")


def reg_value(root: str, path: str, name: str):
    """reg query 로 값 하나를 읽는다. 없으면 None."""
    done = subprocess.run(["reg", "query", f"{root}\\{path}", "/v", name], capture_output=True)
    if done.returncode != 0:
        return None
    for line in done.stdout.decode("mbcs", errors="replace").splitlines():
        found = re.match(r"^\s+(.+?)\s{4}(REG_\w+)(?:\s{4}(.*))?$", line)
        if found and found.group(1).strip().lower() == name.lower():
            data = (found.group(3) or "").strip()
            return int(data, 16) if found.group(2) in ("REG_DWORD", "REG_QWORD") else data
    return None


def same(got, want) -> bool:
    return got is not None and o._same(got, want)


def screenshot(name: str) -> None:
    try:
        from PIL import ImageGrab

        ImageGrab.grab().save(OUT / f"{name}.png")
    except Exception as exc:
        note(f"      (화면 사진 실패: {exc})")


def close(windows) -> None:
    import ctypes
    from ctypes import wintypes

    post = ctypes.windll.user32.PostMessageW
    post.argtypes = [wintypes.HWND, wintypes.UINT, wintypes.WPARAM, wintypes.LPARAM]
    for hwnd, *_ in windows:
        post(hwnd, 0x0010, 0, 0)        # WM_CLOSE


def open_and_look(key: str) -> list:
    """exe 로 확인 창을 열고, 새로 뜬 창의 종류·제목·크기·위치를 적고, 사진을 찍는다."""
    before = {window[0] for window in o.top_windows()}
    process = subprocess.Popen([EXE, "show", key], stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    time.sleep(8)
    fresh = [window for window in o.top_windows() if window[0] not in before]
    for _, kind, title, (left, top, right, bottom) in fresh:
        note(f"      새 창: [{kind}] '{title}' {right - left}x{bottom - top} 위치 ({left},{top})")
    screenshot(f"view-{key}")
    close(fresh)
    time.sleep(1)
    # exe 는 두 겹(풀어주는 쪽 + 실제 프로그램)으로 돈다. 한 겹만 끄면 나머지가 남는다.
    subprocess.run(["taskkill", "/PID", str(process.pid), "/T", "/F"], capture_output=True)
    try:
        output = process.communicate(timeout=15)[0].decode("utf-8", errors="replace").strip()
    except subprocess.TimeoutExpired:
        output = "(출력을 못 읽음)"
    if output:
        note("      " + output.replace("\n", "\n      "))
    return fresh


def main() -> int:
    # GitHub 윈도우 컴퓨터는 영어판이라 콘솔이 한글을 못 찍는다
    for stream in (sys.stdout, sys.stderr):
        stream.reconfigure(encoding="utf-8", errors="replace")
    OUT.mkdir(exist_ok=True)
    note("=== 0. 준비 — 가짜 서든어택 (실행 파일 위치만 있으면 된다) ===")
    game = Path(r"C:\Nexon\SuddenAttack")
    game.mkdir(parents=True, exist_ok=True)
    shutil.copy(r"C:\Windows\System32\notepad.exe", game / "SuddenAttack.exe")

    ctx = o.build_context(OUT / "source-root")
    check("서든어택 설치 위치를 찾는다", ctx.install is not None, str(ctx.install and ctx.install.exe))
    keys = o.Optimizer(ctx).recommended_keys()
    note("이 컴퓨터에서 적용할 권장 항목: " + ", ".join(keys))
    catalog = o.by_key()
    items = [(key, item) for key in keys if isinstance(catalog[key].action, o.RegistryAction)
             for item in catalog[key].action.items(ctx)]
    before = {(item.root, item.path, item.name): reg_value(item.root, item.path, item.name)
              for _, item in items}
    plan_before = o._parse_scheme(shell("powercfg", "/getactivescheme"))
    note(f"지금 전원 계획: {plan_before}")

    note()
    note("=== 1. 적용 전 ===")
    run("--version")
    run("status")
    run("measure")

    note()
    note("=== 2. 적용 — 그리고 윈도우 도구로 하나하나 확인 ===")
    code, _ = run("apply")
    check("apply 가 끝까지 성공한다", code == 0)
    for key, item in items:
        got = reg_value(item.root, item.path, item.name)
        check(f"{key} · {item.name}", same(got, item.value.data),
              f"reg query = {got!r} (원하는 값 {item.value.data!r})")
    if "power_plan" in keys:
        active = shell("powercfg", "/getactivescheme").strip()
        check("전원 계획이 우리 것으로 바뀐다", "SA-Optimizer" in active, active)
        check("최소 프로세서 상태(전원 연결)가 100% 다", o.processor_minimum(ctx) == 100,
              f"{o.processor_minimum(ctx)}%")
    live = o.system_mouse()             # 원래 꺼져 있던 컴퓨터여도, 적용 뒤에는 꺼져 있어야 한다
    check("마우스 가속이 윈도우가 지금 쓰는 값에서도 꺼진다", live is not None and live[2] == 0,
          f"SPI_GETMOUSE = {live}", soft=True)
    code, text = run("apply")
    check("두 번째 apply 는 아무것도 안 바꾼다", code == 0 and "바꿀 것이 없습니다" in text)
    run("check")
    run("measure")

    note()
    note("=== 3. 확인 창 — 설정이 보이는 윈도우 창이 실제로 뜨는가 (참고) ===")
    for key in o.VIEWS:
        if key in ("defender",):
            continue
        fresh = open_and_look(key)
        check(f"창이 뜬다: {key}", bool(fresh),
              ", ".join(f"{w[1]} '{w[2]}'" for w in fresh) or "새 창 없음", soft=True)

    note()
    note("=== 4. 게임 프레임 측정 — PresentMon 이 도는가 (참고, 게임 대신 화면 합성기) ===")
    animation = subprocess.Popen(["powershell", "-NoProfile", "-Command", ANIMATION])
    time.sleep(4)
    code, text = run("game", "--process", "dwm.exe", "--seconds", "6", "--delay", "0", "--quiet",
                     timeout=120)
    check("PresentMon 으로 장면을 잰다", code == 0 and "fps" in text, soft=True)
    if animation.poll() is None:
        animation.kill()

    note()
    note("=== 5. 되돌리기 — 손대기 전과 똑같아지는가 ===")
    code, _ = run("revert")
    check("revert 가 끝까지 성공한다", code == 0)
    for key, item in items:
        spot = (item.root, item.path, item.name)
        got = reg_value(*spot)
        check(f"되돌림 {key} · {item.name}", got == before[spot], f"{got!r} (원래 {before[spot]!r})")
    if "power_plan" in keys:
        after = o._parse_scheme(shell("powercfg", "/getactivescheme"))
        check("전원 계획이 원래 것으로 돌아간다", after and plan_before and after[0] == plan_before[0],
              str(after))
        check("우리가 만든 전원 계획은 지워진다", "SA-Optimizer" not in shell("powercfg", "/list"))

    note()
    note("=== 6. 백신 검사 제외 (선택 항목, 참고) ===")
    code, _ = run("apply", "--only", "defender")
    listed = shell("powershell", "-NoProfile", "-Command", "(Get-MpPreference).ExclusionPath")
    if check("검사 제외에 게임 폴더가 들어간다", code == 0 and str(game) in listed, soft=True):
        run("revert")
        listed = shell("powershell", "-NoProfile", "-Command", "(Get-MpPreference).ExclusionPath")
        check("되돌리면 검사 제외에서 빠진다", str(game) not in listed, soft=True)

    note()
    note("=== 7. 찌꺼기 비우기 — 오래된 임시 파일만 지우고 최근 것은 남기는가 ===")
    temp = Path(os.environ["TEMP"]) / "sa-e2e-junk"
    temp.mkdir(exist_ok=True)
    old, fresh = temp / "old.tmp", temp / "fresh.tmp"
    old.write_bytes(b"x" * 4096)
    fresh.write_bytes(b"x" * 4096)
    stale = time.time() - 3 * 24 * 3600
    os.utime(old, (stale, stale))
    code, text = run("clean")
    check("clean 이 끝까지 성공한다", code == 0 and "비웠습니다" in text)
    check("사흘 된 임시 파일은 지워진다", not old.exists())
    check("방금 만든 임시 파일은 남는다", fresh.exists())
    shutil.rmtree(temp, ignore_errors=True)

    note()
    note(f"=== 결과: 실패 {len(FAILED)}개 · 참고-실패 {len(SOFT)}개 ===")
    for name in FAILED:
        note(f"  FAIL {name}")
    for name in SOFT:
        note(f"  참고 {name}")
    (OUT / "report.txt").write_text("\n".join(REPORT), encoding="utf-8")
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
