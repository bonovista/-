"""Build a preview copy of the expense-ledger guide with the Stageshow demo
in place of the two "돈을 썼을 때" screenshots. The live guide is untouched."""
import base64
import re
import sys

guide_path, dist, fonts, out_path = sys.argv[1:5]
h = open(guide_path, encoding='utf8').read()

# The saved page carries the publish skeleton; the publish adds it again
body_at = h.find('<body>')
if body_at != -1:
    h = h[body_at + len('<body>'):]
h = re.sub(r'</body>\s*</html>\s*$', '', h)

# Name the preview apart from the live guide
h = h.replace('<title>온라인 비용 장부 사용 안내</title>', '<title>비용 장부 안내 시안</title>', 1)

# One Pretendard subset for the guide and the demo: 400, 500, 600
def face(weight, name):
    data = base64.b64encode(open(f'{fonts}/P-{name}.woff2', 'rb').read()).decode()
    return f"@font-face {{ font-family: 'Pretendard'; src: url('data:font/woff2;base64,{data}') format('woff2'); font-weight: {weight}; font-display: swap; }}"

old_faces = re.findall(r"@font-face \{ font-family: 'Pretendard';[^}]*\}", h)
assert len(old_faces) == 2, len(old_faces)
h = h.replace(old_faces[0], '\n'.join([face(400, 'Regular'), face(500, 'Medium'), face(600, 'SemiBold')]), 1)
h = h.replace(old_faces[1], '', 1)

# The "돈을 썼을 때" figures become the demo
start = h.find('<h3>돈을 썼을 때</h3>')
shots = h.find('<div class="shots">', start)
end = h.find('</div>', h.find('</figure>', h.find('</figure>', shots) + 1)) + len('</div>')
assert start != -1 and shots != -1
demo = '''<div class="shots demo">
        <figure>
          <div id="bv-expense-demo" class="demo-stage" role="img" aria-label="쓴 돈 기록 화면. 금액에 30,000원을 적고, 거래처의 국제세탁 단추를 누르면 종류의 세탁이 같이 선택되고, 품목 가죽다림을 두 번 눌러 2건이 됩니다."></div>
          <figcaption class="demo-cap"><span>금액부터 품목까지</span><button type="button" id="bv-expense-replay" class="replay">다시 보기</button></figcaption>
        </figure>
      </div>'''
h = h[:shots] + demo + h[end:]

# Figure rules for the demo, at the end of the page's own stylesheet
rules = '''
.shots.demo { display: block; overflow: visible; padding-bottom: 0; }
.shots.demo figure { flex: none; width: 100%; display: grid; gap: 6px; }
.demo-stage { min-height: 600px; }
.demo-cap { display: flex; justify-content: space-between; align-items: center; gap: 12px; font-size: 13px; line-height: 1.5; color: var(--mute); }
.replay { font: 600 14px/1 var(--sans); color: var(--ink); background: none; border: 0; padding: 0 2px; min-height: 40px; text-decoration: underline; text-underline-offset: 3px; cursor: pointer; }
.replay:hover { color: var(--accent); }
@media (min-width: 860px) {
  .body.split.two .shots.demo { width: 572px; }
  .body.split .shots.demo figure { width: 100%; }
  .demo-stage { min-height: 680px; }
}
'''
first_style_end = h.find('</style>', h.find('<style>', h.find('<title>')))
h = h[:first_style_end] + rules + h[first_style_end:]

css = open(f'{dist}/bv-expense.css', encoding='utf8').read()
js = open(f'{dist}/bv-expense.js', encoding='utf8').read().replace('</script', '<\\/script')
h = h.rstrip() + f'\n<style>\n/* Stageshow demo (bv-expense) */\n{css}\n</style>\n<script>\n{js}\n</script>\n'

open(out_path, 'w', encoding='utf8').write(h)
print('written', out_path, len(h.encode()) // 1024, 'KB')
