import { Stage, Phone, Button, Bar, Collapse, Icon, type Act } from '../../kit'
import '../bv-expense/fonts.css'
import '../bv-expense/expense.css'
import './payment.css'

// The lower half of the same "쓴 돈 기록" sheet, for the guide's "영수증과
// 외상" block. Three beats: 현금 is tapped and the cash-receipt note opens
// under it (카드전표 goes quiet at the same time: a cash payment has no card
// slip); 복사 is tapped and confirms on itself; 지출증빙 현금영수증 is chosen.
// Plays once; the payoff is the still.
//
// Real strings: the title, 결제 and its three options, the note with the
// business number, 복사, 증빙 and its five options. 용도 above and 날짜, 메모,
// 사진 below are filler.

type S = { pay: boolean; copied: boolean; proof: boolean }

const START: S = { pay: false, copied: false, proof: false }
const POSTER: S = { pay: true, copied: true, proof: true }

// The guide's own example number: every screen in it is an example
const BIZ_NO = '123-45-67890'

const script = async (a: Act<S>) => {
  await a.wait(1000)
  a.mark('cash')
  await a.click({ at: 'cash', x: 0.8, y: 0.62 })
  a.put({ pay: true })
  // Reading time for the note before its button is used
  await a.wait(1800)
  a.mark('copy')
  await a.click({ at: 'copy', x: 0.82, y: 0.62 })
  a.put({ copied: true })
  await a.wait(1200)
  a.mark('proof')
  await a.click({ at: 'proof', x: 0.88, y: 0.62 })
  a.put({ proof: true })
  a.mark('done')
  await a.wait(2800)
}

function Label({ children }: { children: string }) {
  return <div className="bv-label">{children}</div>
}

function FillerField({ label, value }: { label: number; value: number }) {
  return (
    <section className="bv-sec bv-filler">
      <Bar w={label} h={8} r={2} tone={3} />
      <div className="bv-fbox">
        <Bar w={value} h={8} r={2} tone={2} />
      </div>
    </section>
  )
}

export default function Payment() {
  return (
    <Stage<S>
      width={572}
      height={630}
      compact={{ below: 572, width: 358, height: 582 }}
      initial={START}
      poster={POSTER}
      script={script}
      play="once"
      cursor={{ at: { wide: { x: 520, y: 640 }, compact: { x: 330, y: 570 } }, style: 'touch', ripple: true }}
      className="bv"
    >
      {(s, _rect, layout) => (
        <Phone width={layout === 'compact' ? 302 : 360} frame="outline" status className="bv-phone">
          <div className="bv-sheet">
            <div className="bv-head">
              <span className="bv-title">쓴 돈 기록</span>
              <span className="bv-close">닫기</span>
            </div>

            <form className="bv-body">
              {/* The end of 품목 and 용도, the rows above, scrolled up under the header */}
              <section className="bv-sec bv-filler">
                <div className="bv-chips">
                  {[56, 34, 42, 34].map((w, i) => (
                    <span key={i} className="bv-chip">
                      <Bar w={w} h={8} r={2} tone={2} />
                    </span>
                  ))}
                </div>
              </section>
              <section className="bv-sec bv-filler">
                <Bar w={30} h={8} r={2} tone={3} />
                <div className="bv-seg">
                  {[44, 70, 34].map((w, i) => (
                    <span key={i} className="bv-seg__cell">
                      <Bar w={w} h={8} r={2} tone={2} />
                    </span>
                  ))}
                </div>
              </section>

              <section className="bv-sec">
                <Label>결제</Label>
                <div className="bv-join">
                  <Button className="bv-opt" data-on={s.pay || undefined} data-target="cash">현금</Button>
                  <Button className="bv-opt">보노비스타 카드</Button>
                  <Button className="bv-opt">계좌이체</Button>
                </div>
                <Collapse open={s.pay} reveal="drop">
                  <div className="bv-note">
                    {/* The instruction and the number it asks for read as one item; 복사 sits beside the number */}
                    <div className="bv-note__copy">
                      <div className="bv-note__text">현금으로 낼 때는 지출증빙용 현금영수증으로 요청하세요.</div>
                      <span className="bv-note__biz">
                        사업자번호 <span className="bv-num">{BIZ_NO}</span>
                      </span>
                    </div>
                    <Button className="bv-copy" icon={s.copied ? <Icon name="check" size={14} stroke={2.2} /> : undefined} data-target="copy">
                      {s.copied ? '복사됨' : '복사'}
                    </Button>
                  </div>
                </Collapse>
              </section>

              <section className="bv-sec">
                <Label>증빙</Label>
                <div className="bv-proof">
                  <Button className="bv-opt bv-opt--wide" data-on={s.proof || undefined} data-target="proof">지출증빙 현금영수증</Button>
                  <Button className="bv-opt" data-off={s.pay || undefined}>카드전표</Button>
                  <Button className="bv-opt">간이영수증</Button>
                  <Button className="bv-opt">세금계산서</Button>
                  <Button className="bv-opt">없음</Button>
                </div>
              </section>

              <FillerField label={30} value={92} />
              <FillerField label={30} value={128} />
              <FillerField label={58} value={116} />
            </form>
          </div>
        </Phone>
      )}
    </Stage>
  )
}
