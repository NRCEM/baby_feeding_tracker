# scripts/import_history.py
# -*- coding: utf-8 -*-
import re
import requests
from datetime import date

API = "http://127.0.0.1:8000"  # FastAPI đang chạy uvicorn app:app --reload
BASE_YEAR = 2025  # Năm của dữ liệu tháng 7 (đổi nếu cần)

# Luật mặc định khi KHÔNG ghi loại sữa
#  Tháng 7: ngày <= 20 -> me, từ 21 trở đi -> pre
MONTH_RULES = {
    7: {"cutover": 21, "before": "me", "after": "pre"},
    # Nếu sau này muốn thêm tháng khác, thêm ở đây.
}

# BỎ QUA sự kiện "hút sữa" (pump)
INCLUDE_PUMPING = False

# ==== DÁN THÔNG TIN THÁNG 7 VÀO ĐÂY ====
RAW = r"""
Ăn Anna tháng 7

1/7
0:00 65mil sữa mẹ
3h 45mil sữa mẹ
4h30 hút sữa 110mil
6h 80mil sữa mẹ
9h30 hút sữa 90mil
10h 90mil sữa mẹ

13h hút sữa 70mil
13h30 70mil sữa mẹ
16h30 50mil (40mil sữa mẹ 10mil sct)
18h hút sữa 75mil
21h 80mil (75mil sữa mẹ 5mil sct)
23h hút sữa 70mil

2/7
0h 40mil sữa mẹ
3h 30mil sct
5h30 hút sữa 100mil
6h 30mil sct
8h15 60mil sữa mẹ
9h30 hút sữa 70mil
10h 30mil sct
12h 60mil sct
13h hút sữa 50mil
16h 70mil sữa mẹ
17h hút sữa 90mil
18h 30mil sct
21h hút sữa 70mil
21h 70mil sữa mẹ
23h30 hút sữa 60mil

3/7
0h 60mil sữa mẹ
2h15 40mil sct
4h15 30mil sct
8h hút sữa 140mil
8h 50mil sữa mẹ
10h40 20mil sữa mẹ
11h30 40mil sữa mẹ + 30mil sct
13h hút sữa 100mil
14h30 60mil sữa mẹ
17h hút sữa 80mil
19h40 80mil sữa mẹ
21h hút sữa 80mil
22h 40mil sữa mẹ
0h 30mil sct

4/7
3h30 30mil sữa mẹ
3h50 hút sữa 110mil
7h30 60mil sữa mẹ
8h15 hút sữa 100mil
11h30 30mil sữa mẹ + 30mil sct
12h hút sữa 80mil
15h30 60mil sữa mẹ
16h 15mil sct
16h50 hút sữa 80mil
17h30 30mil sữa mẹ
20h hút sữa 80mil
21h 30mil sữa mẹ
23h30 50mil sữa mẹ

5/7
0:30 hút sữa 70mil
2h40 40mil sữa mẹ
6h 50mil sữa mẹ
7h 20mil sữa mẹ
8h30 30mil sữa mẹ+ 10mil sct
10h40 hút sữa 80mil
11h 50mil sữa mẹ
13h hút sữa 45mil
14h30 40mil sữa mẹ
17h 70mil sữa mẹ
17h30 hút sữa 60mil
21h hút sữa 60mil
21h30 60mil sữa mẹ

6/7
0h30 40mil sữa mẹ
3h30 40mil sữa mẹ
3h30 hút sữa 120mil
6h30 60mil sữa mẹ
7h hút sữa 70mil
8h 40mil sct
10h hút sữa 50mil
12h30 60mil sữa mẹ
13h30 hút sữa 70mil
14h30 60mil sữa mẹ
16h30 hút sữa 60mil
17h 30mil sữa mẹ
18h 50mil sct
23h 40mil sữa mẹ

7/7
2h 50mil sữa mẹ
5h30 hút sữa 120mil
6h 50mil sữa mẹ
9h 60mil sữa mẹ
10h40 hút sữa 110mil
11h30 40mil sữa mẹ
15h 50mil sữa mẹ
16h 30mil sữa mẹ
16h hút sữa 120mil
18h 40mil sữa mẹ
19h 30mil sữa mẹ
19h hút sữa 70mil
20h 30mil sữa mẹ
23h30 hút sữa 80mil

8/7
0h 50mil sữa mẹ
2h30 30mil sữa mẹ
4h hút sữa 100mil
5h30 50mil sữa mẹ
8h30 50mil sữa mẹ
9h30 hút sữa 120mil
12h 50mil sữa mẹ
15h30 hút sữa 110mil
15h30 70mil sữa mẹ
18h 40mil sữa mẹ
20h hút sữa 120mil
21h 40mil sữa mẹ
23h hút sữa 70mil

9/7
0h 50mil
3h 30mil
6h 50mil
7h30 hút sữa 150mil
9h 40mil
11h30 hút sữa 80mil
12h 50mil
15h 30mil
16h hút sữa 100mil
18h 70mil
23h hút sữa 80mil

10/7
6h hút sữa (nhanh) 80mil
9h hút sữa 100mil
13h hút sữa 90mil
16h hút sữa 60mil
19h hút sữa 70mil
22h hút sữa 80mil

11/7
6h30 hút sữa 150mil
9h30 hút sữa 40mil
14h hút sữa 90mil
18h hút sữa 90mil
18h30 50mil
22h 50mil
22h30 hút sữa 90mil

12/7
1h 40mil
3h 60mil
3h hút sữa 120mil
6h 50mil
8h 50mil
9h30 hút sữa 130mil
11h 60mil
15h hút sữa 110mil
15h 60mil
17h30 20mil
18h hút sữa 90mil
20h 60mil
21h hút sữa 80mil
23h 40mil

13/7
2h 30mil
2h hút sữa 100mil
4h 20mil
5h30 40mil
8h hút sữa 130mil
8h 40mil
10h30 50mil
13h hút sữa 110mil
14h 50mil
18h 30mil
18h hút sữa 130mil
21h 80mil

14/7
4h 60mil
4h30 hút sữa 140mil
7h 60mil
8h30 hút sữa 100mil
10h 60mil
12h hút sữa 90mil
13h 40mil
16h hút sữa 80mil
17h 50mil
19h30 hút sữa 100mil
20h 30mil
23h hút sữa 80mil
23h 30mil

15/7
2h 30mil
2h30 hút sữa 80mil
4h 30mil
8h 70mil
8h30 hút sữa 140mil
10h30 20mil
11h30 30mil
12h hút sữa 80mil
14h30 40mil
15h30 hút sữa 80mil
16h30 20mil
18h 40mil 
19h hút sữa 90mil
21h 10ml
23h 60ml

16/7
0h hút sữa 120ml
1h 30mil
4h30 30mil
5h hút sữa 100mil
7h30 80mil
9h30 hút sữa 110mil
10h 10mil
11h 70mil
13h30 hút sữa 90mil
14h 50mil
15h 30mil
15h30 30mil
18h30 60mil
19h 30mil
19h30 hút sữa 150mil
21h30 30mil
22h30 hút sữa 90mil
23h30 30mil

17/7
2h 60mil
5h 10mil
7h 50mil
7h30 hút sữa 180mil
10h 90mil
12h hút sữa 110mil
12h45 50mil
16h30 70mil
18h hút sữa 170mil
19h 40mil
22h hút sữa 100mil

18/7
0h30 40mil
3h30 50mil
4h hút sữa 150mil
6h 50mil
8h 60mil
10h 20mil
11h hút sữa 110mil
11h30 30mil
12h 30mil
15h 60mil
16h 30mil
17h hút sữa 160mil
17h30 30mil
19h 60mil
20h hút sữa 100mil

19/7
1h 50mil
2h hút sữa 100mil
4h 30mil
7h 30mil
7h30 hút sữa 160mil
11h 50mil
11h30 hút sữa 100mil
12h 30mil
14h30 80mil
17h 40mil
17h hút sữa 120mil
20h 30mil
20h hút sữa 100mil
22h 20mil

20/7
2h30 50mil
3h hút sữa 150mil
6h30 50mil
7h30 50mil
9h hút sữa 130mil
10h 50mil
11h 50mil
12h hút sữa 100mil
15h 50mil
16h 50mil
17h hút sữa 80mil
18h 50mil
20h30 80mil
22h30 hút sữa 60mil

21/7
0h 75mil
1h 30mil
4h 80mil
4h30 hút sữa 130mil
6h30 130mil
8h30 hút sữa 100mil
10h 50mil
11h30 85mil
12h30 hút sữa 100mil
13h 110mil
17h 100mil
17h30 hút sữa 120mil
21h30 100mil
22h hút sữa 160mil

22/7
2h30 90mil
3h30 hút sữa 120mil
5h30 50mil
7h30 40mil
9h 30mil
9h hút sữa 160mil
11h 60mil
12h hút sữa 80mil
15h 50mil
16h30 hút sữa 100mil
17h30 50mil
18h00 20mil
19h30 40mil
20h50 40mil
21h30 hút sữa 130mil

23/7
2h30 40mil
3h30 50mil
5h30 60mil
5h30 hút sữa 200mil
8h30 60mil
9h30 hút sữa 100mil
11h 50mil
12h30 hút sữa 100mil 
13h30 50mil
16h 40mil
17h hút sữa 110mil
17h 30mil
18h30 80mil
20h30 hút sữa 100mil
22h 30mil

24/7
2h30 20mil
3h30 50mil
5h hút sữa 200mil
7h 40mil
8h30 30mil
10h hút sữa 150mil
12h30 hút sữa 80mil
13h20 70mil
15h 30mil
15h15 40mil
16h25 60mil
17h hút sữa 100mil
19h15 60mil
19h50 50mil
20h30 30mil
20h30 hút sữa 110mil

25/7
3h 120mil
4h hút sữa 150mil
5h30 60mil
8h30 60mil
9h30 hút sữa 130mil
10h30 80mil
14h hút sữa 100mil
15h 90mil
16h30 20mil sau ị, để đi ngủ
17h30 40mil thức ăn ngủ lại liền
23h 90mil

26/7
1h 70mil
5h 100mil
8h30 100mil
9h hút sữa 200mil
12h 70mil
14h hút sữa 140mil
15h30 60mil
17h 10mil
18h hút sữa
19h30 90mil
21h 30mil
21h hút sữa

27/7
2h30 60mil
4h 60mil
5h30 60mil
8h30 hút sữa 180mil
10h30 50mil
14h 70mil
15h hút sữa 100mil
17h30 100mil
19h 30mil
19h hút sữa 120mil
20h30 30mil
22h hút sữa 90mil

28/7
0h 60mil
2h30 20mil
4h 20mil
4h30 hút sữa 110mil
8h 40mil
9h30 hút sữa 140mil (hút k liên tục đến 11h)
11h 40mil
13h40 30mil
14h hút sữa 60mil
15h30 40mil
17h 20mil
18h 50mil
20h hút sữa 100mil
20h30 60mil

29/7
Cữ 1
1h15 60mil
Cữ 2
4h40 60mil
Cữ 3
6h30 dậy
7h30 40mil
8h ngủ
Cữ 4
9h15 dậy tắm
10h 40mil, nap
11h 70mil
12h30 ngủ
Cữ 5
15h30 70mil
16h chơi
17h nap
17h30 30mil
18h ngủ
Cữ 6
19h15 50mil
Cữ 7
21h20 20mil
Cữ 8
11h30 80mil

30/7
Cữ 1
3h30 30mil ăn xong ngủ
Cữ 2
7h15 60mil ăn xong ngủ
Cữ 3
9h 20mil
Chơi
Tắm đến 10h
10h 70mil
Chơi
11h20 ngủ
Cữ 4
13h 60mil ăn xong ngủ
Cữ 5
14h dậy chơi
14h30 30mil
16h 10mil 
16h20 ngủ
Cữ 6
17h 50mil
Chơi
18h30 20mil
19h ngủ
Cữ 7
20h 40mil
Cữ 8
21h30 20mil
22h30 30mil
"""

# ============ Regex & helpers ============
DATE_RE = re.compile(r"^\s*(\d{1,2})/(\d{1,2})\s*$")

# Giờ: 3h, 3h30, 0:00, 21:45; đơn vị ml/mil; type tuỳ chọn
ITEM_RE = re.compile(
    r"^\s*(?:(\d{1,2})h(?:(\d{1,2}))?|(\d{1,2}):(\d{2}))\s+(\d{1,4})\s*m(?:il|l)\s*(?:\s*(sct|pre|sữa mẹ|me|mẹ))?\s*$",
    flags=re.IGNORECASE,
)

PAREN_RE = re.compile(r"\(([^)]+)\)")  # phần trong ngoặc
TYPE_MAP = {"sct": "sct", "pre": "pre", "sữa mẹ": "me", "mẹ": "me", "me": "me"}
NOISE = {"cữ", "tắm", "ngủ", "chơi", "đi tiêm phòng", "k nhớ", "dậy", "thức", "nap"}


def is_noise(line: str) -> bool:
    s = line.strip().lower()
    if not s:
        return True
    if s.startswith("ăn anna"):
        return True
    if not INCLUDE_PUMPING and "hút sữa" in s:
        return True
    # nếu chứa từ noise và không có số ml thì bỏ
    if any(x in s for x in NOISE) and ("ml" not in s and "mil" not in s):
        return True
    return False


def to_iso(y, m, d) -> str:
    return date(y, m, d).isoformat()


def default_type_for(iso: str) -> str:
    y, m, d = map(int, iso.split("-"))
    rule = MONTH_RULES.get(m)
    if not rule:
        return "me"  # fallback: không có luật riêng thì mặc định sữa mẹ
    return rule["before"] if d < rule["cutover"] else rule["after"]


def parse_segments_in_paren(paren_text: str):
    parts = re.findall(
        r"(\d{1,4})\s*m(?:il|l)\s*(sct|pre|sữa mẹ|me|mẹ)?",
        paren_text.strip(),
        flags=re.IGNORECASE,
    )
    out = []
    for amt, t in parts:
        t = t.lower() if t else None
        out.append((int(amt), TYPE_MAP.get(t) if t else None))
    return out


def parse_line(line: str, current_date_iso: str, default_type: str):
    """
    Trả về list record [{'date','time','amount','milk_type'}].
    Hỗ trợ:
      - "15h30 70ml me"
      - "21:45 80ml"
      - "11h30 40ml sữa mẹ + 30ml sct"
      - "16h30 50ml (40ml sữa mẹ 10ml sct)"
    """
    s = line.strip()
    if not s:
        return []

    # có ngoặc -> tách theo ngoặc
    m_par = PAREN_RE.search(s)
    if m_par:
        m_time = re.match(r"^\s*(?:(\d{1,2})h(?:(\d{1,2}))?|(\d{1,2}):(\d{2}))\s+", s)
        if not m_time:
            return []
        if m_time.group(1) is not None:
            hh = int(m_time.group(1))
            mm = int(m_time.group(2) or 0)
        else:
            hh = int(m_time.group(3))
            mm = int(m_time.group(4))
        time_iso = f"{hh:02d}:{mm:02d}"
        segs = parse_segments_in_paren(m_par.group(1))
        return [
            {
                "date": current_date_iso,
                "time": time_iso,
                "amount": amt,
                "milk_type": t or default_type,
            }
            for amt, t in segs
        ]

    # có dấu cộng -> tách các đoạn sau time
    if "+" in s:
        m_time = re.match(r"^\s*(?:(\d{1,2})h(?:(\d{1,2}))?|(\d{1,2}):(\d{2}))\s+", s)
        if not m_time:
            return []
        if m_time.group(1) is not None:
            hh = int(m_time.group(1))
            mm = int(m_time.group(2) or 0)
        else:
            hh = int(m_time.group(3))
            mm = int(m_time.group(4))
        time_iso = f"{hh:02d}:{mm:02d}"
        tail = s[m_time.end() :]
        out = []
        for seg in [p for p in tail.split("+") if p.strip()]:
            m = re.search(
                r"(\d{1,4})\s*m(?:il|l)\s*(sct|pre|sữa mẹ|me|mẹ)?",
                seg,
                flags=re.IGNORECASE,
            )
            if not m:
                continue
            amt = int(m.group(1))
            t = m.group(2).lower() if m.group(2) else None
            out.append(
                {
                    "date": current_date_iso,
                    "time": time_iso,
                    "amount": amt,
                    "milk_type": TYPE_MAP.get(t) if t else default_type,
                }
            )
        return out

    # dòng thường
    m = ITEM_RE.match(s)
    if not m:
        return []
    if m.group(1) is not None:  # 3h / 3h30
        hh = int(m.group(1))
        mm = int(m.group(2) or 0)
    else:  # 03:30
        hh = int(m.group(3))
        mm = int(m.group(4))
    amt = int(m.group(5))
    t_raw = m.group(6).lower() if m.group(6) else None
    milk = TYPE_MAP.get(t_raw) if t_raw else default_type
    return [
        {
            "date": current_date_iso,
            "time": f"{hh:02d}:{mm:02d}",
            "amount": amt,
            "milk_type": milk,
        }
    ]


# ============ main ============
def main():
    current_date_iso = None
    rows = []

    for raw_line in RAW.splitlines():
        line = raw_line.strip()
        dm = DATE_RE.match(line)
        if dm:
            dd = int(dm.group(1))
            mm = int(dm.group(2))
            current_date_iso = to_iso(BASE_YEAR, mm, dd)
            continue
        if not current_date_iso:
            continue
        if is_noise(line):
            continue

        default_type = default_type_for(current_date_iso)
        rows.extend(parse_line(line, current_date_iso, default_type))

    # preview
    print(f"Parsed {len(rows)} feedings. Ví dụ 8 bản ghi đầu:")
    for r in rows[:8]:
        print(r)

    ans = input("Gửi vào API FastAPI? (y/N): ").strip().lower()
    if ans != "y":
        print("Bỏ qua gửi API.")
        return

    ok = 0
    fail = 0
    for r in rows:
        try:
            resp = requests.post(f"{API}/feedings", json=r, timeout=5)
            if resp.ok:
                ok += 1
            else:
                fail += 1
                print("FAIL:", r, "->", resp.status_code, resp.text[:200])
        except Exception as e:
            fail += 1
            print("ERR:", r, "->", e)

    print(f"Done. OK={ok}, FAIL={fail}")


if __name__ == "__main__":
    main()
