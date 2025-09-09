import streamlit as st
import streamlit.components.v1 as components
import random
import html
from typing import Tuple

st.set_page_config(page_title="서아의 연산 학습지", page_icon="🧮", layout="wide")

# -----------------------------
# 유틸
# -----------------------------
def make_rng(seed: str) -> random.Random:
    return random.Random(seed)

def digits_range(d: int) -> Tuple[int, int]:
    if d == 1: return (1, 9)
    if d == 2: return (10, 99)
    if d == 3: return (100, 999)
    raise ValueError("digits must be 1..3")

def randint_r(rng: random.Random, a: int, b: int) -> int:
    return rng.randint(a, b)

# -----------------------------
# 문제 생성기 (carry/borrow 옵션 반영)
# -----------------------------
def gen_addition(rng, aD, bD, allow_carry=True):
    amin, amax = digits_range(aD)
    bmin, bmax = digits_range(bD)
    tries = 0
    while True:
        a = randint_r(rng, amin, amax)
        b = randint_r(rng, bmin, bmax)
        if allow_carry:
            return a, "+", b
        # 받아올림 없는 덧셈: 각 자리 합 < 10
        width = max(len(str(a)), len(str(b)))
        a_s = str(a).zfill(width)
        b_s = str(b).zfill(width)
        if all(int(x) + int(y) < 10 for x, y in zip(a_s[::-1], b_s[::-1])):
            return a, "+", b
        tries += 1
        if tries > 2000:
            return a, "+", b  # 안전 탈출

def gen_subtraction(rng, aD, bD, allow_borrow=True):
    amin, amax = digits_range(aD)
    bmin, bmax = digits_range(bD)
    tries = 0
    while True:
        a = randint_r(rng, amin, amax)
        b = randint_r(rng, bmin, bmax)
        if a < b:
            a, b = b, a  # 자연수 결과 보장
        if allow_borrow:
            return a, "−", b
        # 받아내림 없는 뺄셈: 각 자리에서 위 자릿수 >= 아래 자릿수
        width = max(len(str(a)), len(str(b)))
        a_s = str(a).zfill(width)
        b_s = str(b).zfill(width)
        if all(int(x) >= int(y) for x, y in zip(a_s[::-1], b_s[::-1])):
            return a, "−", b
        tries += 1
        if tries > 2000:
            return a, "−", b  # 안전 탈출

def gen_multiplication(rng, aD, bD):
    amin, amax = digits_range(aD)
    bmin, bmax = digits_range(bD)
    a = randint_r(rng, amin, amax)
    b = randint_r(rng, bmin, bmax)
    return a, "×", b

def gen_division(rng, dividendD, divisorD):
    # 나누어떨어지는 경우만
    dmin, dmax = digits_range(divisorD)
    divisor = max(1, randint_r(rng, dmin, dmax))
    if dividendD == 1:
        cands = [v for v in range(1, 9 + 1) if v % divisor == 0]
        if not cands:
            # 안전쌍
            for (a, b) in [(8, 4), (9, 3), (6, 3), (6, 2), (4, 2)]:
                if divisor == b:
                    return a, "÷", b
            return 8, "÷", 4
        return cands[randint_r(rng, 0, len(cands) - 1)], "÷", divisor

    vmin, vmax = digits_range(dividendD)
    q_min, q_max = 1, (99 if dividendD == 2 else 999)
    tries = 0
    while True:
        q = randint_r(rng, q_min, q_max)
        dividend = q * divisor
        if vmin <= dividend <= vmax:
            return dividend, "÷", divisor
        if tries % 50 == 49:
            divisor = max(1, randint_r(rng, dmin, dmax))
        tries += 1
        if tries > 2000:
            return divisor * 12, "÷", divisor  # 안전 탈출

# -----------------------------
# 챕터 메타 (digits와 op를 저장)
# -----------------------------
CHAPTERS = {
    "addition": [
        ("1d+1d", "한자리수 + 한자리수",       (1, 1)),
        ("2d+1d", "두자리수 + 한자리수",       (2, 1)),
        ("2d+2d", "두자리수 + 두자리수",       (2, 2)),
        ("3d+2d", "세자리수 + 두자리수",       (3, 2)),
        ("3d+3d", "세자리수 + 세자리수",       (3, 3)),
    ],
    "subtraction": [
        ("1d-1d", "한자리수 − 한자리수 (자연수)", (1, 1)),
        ("2d-1d", "두자리수 − 한자리수 (자연수)", (2, 1)),
        ("2d-2d", "두자리수 − 두자리수 (자연수)", (2, 2)),
        ("3d-2d", "세자리수 − 두자리수 (자연수)", (3, 2)),
        ("3d-3d", "세자리수 − 세자리수 (자연수)", (3, 3)),
    ],
    "multiplication": [
        ("1d×1d", "한자리수 × 한자리수",       (1, 1)),
        ("2d×1d", "두자리수 × 한자리수",       (2, 1)),
        ("2d×2d", "두자리수 × 두자리수",       (2, 2)),
        ("3d×1d", "세자리수 × 한자리수",       (3, 1)),
        ("3d×2d", "세자리수 × 두자리수",       (3, 2)),
    ],
    "division": [
        ("1d÷1d", "한자리수 ÷ 한자리수 (정확히 나눔)", (1, 1)),
        ("2d÷1d", "두자리수 ÷ 한자리수 (정확히 나눔)", (2, 1)),
        ("3d÷1d", "세자리수 ÷ 한자리수 (정확히 나눔)", (3, 1)),
    ],
}

OP_TITLES = {
    "addition": "덧셈",
    "subtraction": "뺄셈 (자연수 결과)",
    "multiplication": "곱셈",
    "division": "나눗셈 (나누어떨어짐)",
}

# -----------------------------
# 사이드바 UI
# -----------------------------
st.sidebar.title("서아의 연산 학습지")

# 사이드바 버튼 줄바꿈 방지 & 크기 통일
st.markdown("""
<style>
section[data-testid="stSidebar"] .stButton > button {
  width: 100%;
  font-size: 0.95rem;
  padding: 8px 10px;
  white-space: nowrap;
  line-height: 1.1;
}
</style>
""", unsafe_allow_html=True)

# 레이아웃 & 계산 규칙
layout_type = st.sidebar.radio("문제 배열 방식", ["가로셈", "세로셈"], index=0)
allow_carry = st.sidebar.checkbox("덧셈: 받아올림 허용", True)
allow_borrow = st.sidebar.checkbox("뺄셈: 받아내림 허용", True)

# 람다에서 전역 캡처 문제로 NameError가 나는 환경을 피하기 위해 기본인자로 캡처
_titles = OP_TITLES.copy()
op = st.sidebar.selectbox(
    "연산",
    list(_titles.keys()),
    format_func=lambda k, _t=_titles: _t.get(k, k)
)

chapters_for_op = CHAPTERS[op]
chapter_labels = [c[1] for c in chapters_for_op]
chapter_idx = st.sidebar.radio(
    "챕터",
    range(len(chapters_for_op)),
    format_func=lambda i, _labs=chapter_labels: _labs[i]
)

chapter_key, chapter_label, (aD, bD) = chapters_for_op[chapter_idx]

# 세트 번호 버튼(1~10)
if "set_no" not in st.session_state:
    st.session_state.set_no = 1
st.sidebar.markdown("**연습문제 세트 (1~10)**")
row1 = st.sidebar.columns(5)
row2 = st.sidebar.columns(5)
for i in range(1, 6):
    if row1[i-1].button(str(i), use_container_width=True):
        st.session_state.set_no = i
for i in range(6, 11):
    if row2[i-6].button(str(i), use_container_width=True):
        st.session_state.set_no = i
set_no = st.session_state.set_no

# -----------------------------
# 20문제 생성 (세트 고정)
# -----------------------------
seed = f"{op}|{chapter_key}|set{set_no}|layout:{layout_type}|carry:{allow_carry}|borrow:{allow_borrow}"
rng = make_rng(seed)
problems = []
seen = set()
for _ in range(20):
    guard = 0
    while True:
        if op == "addition":
            a, sym, b = gen_addition(rng, aD, bD, allow_carry=allow_carry)
        elif op == "subtraction":
            a, sym, b = gen_subtraction(rng, aD, bD, allow_borrow=allow_borrow)
        elif op == "multiplication":
            a, sym, b = gen_multiplication(rng, aD, bD)
        else:
            a, sym, b = gen_division(rng, aD, bD)
        sig = f"{a}{sym}{b}"
        if sig not in seen or guard > 50:
            seen.add(sig)
            problems.append((a, sym, b))
            break
        guard += 1

# 정답 계산
def solve(a, sym, b) -> int:
    if sym == "+":  return a + b
    if sym == "−":  return a - b
    if sym == "×":  return a * b
    if sym == "÷":  return a // b  # 나누어떨어짐 보장
    raise ValueError("unknown operator")

answers = [solve(a, s, b) for (a, s, b) in problems]

# -----------------------------
# 세로셈 렌더링
# -----------------------------
def render_vertical(a, sym, b, ans=None):
    a_str, b_str = str(a), str(b)
    width = max(len(a_str), len(b_str))
    a_str = a_str.rjust(width)
    b_str = b_str.rjust(width)
    ans_str = "" if ans is None else str(ans).rjust(width)
    html_block = f"""
    <div class="vwrap">
      <div class="row">{a_str}</div>
      <div class="row">{sym} {b_str}</div>
      <div class="line"></div>
      <div class="row">{ans_str}</div>
    </div>
    """
    return html_block

# -----------------------------
# 시트 HTML (가로/세로 + 정답지 지원)
# -----------------------------
def make_sheet_html(title: str, seed: str, problems, answers=None, layout="가로셈"):
    safe_title = html.escape(title)
    safe_seed  = html.escape(seed)

    # 레이아웃별 그리드/셀 높이 값
    if layout == "가로셈":
        grid_css   = "display:grid; grid-template-columns:1fr 1fr; gap:8px;"
        cell_min_h = "56px"
    else:  # 세로셈
        grid_css   = "display:grid; grid-template-columns:1fr 1fr 1fr 1fr; gap:8px;"
        cell_min_h = "120px"

    css = f"""
    :root {{ --sheet-max: 800px; }}
    html, body {{
      margin: 0; padding: 0; background: transparent;
      font-family: Pretendard, -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, "Apple SD Gothic Neo", "Noto Sans KR", sans-serif;
    }}
    #print-area {{
      width: 100%;
      max-width: var(--sheet-max);
      margin: 24px auto;
      background: white;
      padding: 24px;
      border-radius: 12px;
      box-shadow: 0 6px 20px rgba(0,0,0,0.06);
    }}
    .sheet-header {{ display:flex; align-items:flex-end; justify-content:space-between; margin-bottom:12px; }}
    .sheet-title {{ font-weight:800; font-size: 22px; }}
    .sheet-meta {{ color:#64748b; font-size:12px; }}
    .grid {{ {grid_css} }}
    .cell {{ border:1px solid #cbd5e1; padding:12px 14px; min-height:{cell_min_h}; background:white; }}
    .no {{ font-weight:700; margin-bottom:6px; }}
    .expr {{ font-size:20px; line-height:1.2; text-align:center; letter-spacing:0.5px; }}
    .ans-line {{ width: 120px; border-bottom:1px solid #cbd5e1; height: 28px; display:inline-block; }}
    .ans-filled {{ width: 120px; text-align:center; display:inline-block; }}

    .vwrap {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace; }}
    .vwrap .row {{ text-align: right; font-size: 20px; line-height: 1.2; }}
    .vwrap .line {{ border-top: 1px solid #0f172a; margin: 4px 0; }}
    .vbox {{ display:flex; justify-content:space-between; align-items:flex-start; }}
    .vno {{ width: 28px; font-weight:700; }}

    @media print {{
      @page {{ size: A4 portrait; margin: 12mm; }}
      #print-area {{ box-shadow:none; padding:0; margin:0 auto; }}
      .grid {{ gap:6px; }}
      .cell {{ min-height:{cell_min_h}; }}
      .toolbar {{ display:none; }}
    }}
    .toolbar {{ display:flex; align-items:center; justify-content:space-between; margin:16px auto 24px; max-width:var(--sheet-max); }}
    .print-btn {{ background:#111; color:white; border:none; padding:10px 16px; border-radius:12px; cursor:pointer; }}
    .print-btn:hover {{ opacity:.9; }}
    """

    rows_html_list = []
    for i, (a, sym, b) in enumerate(problems, start=1):
        ans_val = None if answers is None else answers[i-1]
        if layout == "가로셈":
            expr = f"{a} {html.escape(sym)} {b} ="
            if ans_val is not None:
                ans_block = f"<div class='ans-filled'><strong>{ans_val}</strong></div>"
            else:
                ans_block = "<div class='ans-line'></div>"
            inner = (
                f"<div class='no'>{i}.</div>"
                f"<div class='expr'>{expr}</div>"
                f"{ans_block}"
            )
            rows_html_list.append(f"<div class='cell'>{inner}</div>")
        else:
            vhtml = render_vertical(a, sym, b, ans_val)
            inner = (
                f"<div class='vbox'>"
                f"<div class='vno'>{i}.</div>"
                f"<div style='flex:1'>{vhtml}</div>"
                f"</div>"
            )
            rows_html_list.append(f"<div class='cell'>{inner}</div>")

    body_html = "\n".join(rows_html_list)
    title_suffix = "" if answers is None else " · 정답지"

    html_full = f"""
    <!doctype html>
    <html lang="ko">
    <head>
      <meta charset="utf-8" />
      <meta name="viewport" content="width=device-width, initial-scale=1" />
      <title>{safe_title}{title_suffix}</title>
      <style>{css}</style>
    </head>
    <body>
      <div id="print-area">
        <div class="sheet-header">
          <div class="sheet-title">{safe_title}{title_suffix}</div>
          <div class="sheet-meta">문제 수: 20 · Seed: {safe_seed}</div>
        </div>
        <div class="grid">
          {body_html}
        </div>
      </div>
      <div class="toolbar">
        <div style="color:#64748b; font-size:13px;">
          A4 세로 1장 레이아웃 · 같은 세트는 언제 열어도 동일 결과(Seed 고정)
        </div>
        <button class="print-btn" onclick="window.print()">프린트하기</button>
      </div>
    </body>
    </html>
    """
    return html_full

title = f"{OP_TITLES[op]} · {chapter_label} · 세트 {set_no}"
html_problem = make_sheet_html(title, seed, problems, answers=None, layout=layout_type)
html_answer  = make_sheet_html(title, seed, problems, answers=answers, layout=layout_type)

# -----------------------------
# 탭: 문제지 / 정답지
# -----------------------------
tab1, tab2 = st.tabs(["📝 문제지", "✅ 정답지"])
with tab1:
    components.html(html_problem, height=900, scrolling=True)
with tab2:
    components.html(html_answer,  height=900, scrolling=True)

# 사이드바 안내
st.sidebar.info("세트 번호를 버튼으로 선택하세요. 각 탭 하단의 '프린트하기'로 A4 세로 1장에 출력하세요.")
