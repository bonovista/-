import { Minus } from 'lucide-react'
import { Stage, Phone, Field, Button, Bar, Collapse, type Act } from '../../kit'
import './fonts.css'
import './expense.css'

// Bonovista's online expense ledger, the "쓴 돈 기록" sheet, for the staff
// guide's "돈을 썼을 때" section. A flow in an app, told in four beats:
// the amount is typed (context), a vendor button is tapped and the vendor
// field and its kind fill together (the relationship the guide describes),
// the kind's items open, then an item is tapped twice and its count rolls to 2
// (result). Plays once; the payoff is the still.
//
// Real strings: the sheet title, the field labels, the amount, the vendor and
// kind buttons, the items and the count. 용도, 결제 and 증빙 sit below the
// story as filler, where the stage's bottom edge crops the phone.

type S = { amount: string; focus: boolean; vendor: boolean; kind: boolean; items: boolean; count: number }

const START: S = { amount: '', focus: true, vendor: false, kind: false, items: false, count: 0 }
const POSTER: S = { amount: '30000', focus: false, vendor: true, kind: true, items: true, count: 2 }

const VENDORS = ['구두수선', '국제세탁', '국제안감', '데레사수선', '문방구', '물보라', '아뜰리에', '중앙단추']
const PICK_VENDOR = '국제세탁'
const KINDS = ['세탁', '수선', '단추·부자재', '비품', '식음료', '수수료', '기타']
const ITEMS = ['가죽다림', '다림', '드라이', '세탁']

const won = (digits: string) => (digits ? Number(digits).toLocaleString('ko-KR') : '')

const script = async (a: Act<S>) => {
  await a.wait(900)
  a.mark('amount')
  await a.type('amount', '30000', { interval: 95 })
  await a.wait(700)
  a.mark('vendor')
  await a.click({ at: 'vendor', x: 0.72, y: 0.62 })
  a.put({ focus: false, vendor: true })
  // The kind follows its vendor a beat later, then the kind's items open
  await a.wait(320)
  a.put({ kind: true })
  await a.wait(260)
  a.put({ items: true })
  await a.wait(1400)
  a.mark('item')
  await a.click({ at: 'item', x: 0.9, y: 0.62 })
  a.put({ count: 1 })
  await a.wait(760)
  await a.click({ at: 'item', x: 0.9, y: 0.62 })
  a.put({ count: 2 })
  a.mark('done')
  await a.wait(2800)
}

function Label({ children }: { children: string }) {
  return <div className="bv-label">{children}</div>
}

// One option button, the app's own: hairline at rest, ink when chosen
function Opt({ on, label, target }: { on?: boolean; label: string; target?: string }) {
  return (
    <Button className="bv-opt" data-on={on || undefined} data-target={target}>
      {label}
    </Button>
  )
}

function Filler({ label, cells }: { label: number; cells: number[] }) {
  return (
    <section className="bv-sec bv-filler">
      <Bar w={label} h={8} r={2} tone={3} />
      <div className="bv-seg">
        {cells.map((w, i) => (
          <span key={i} className="bv-seg__cell">
            <Bar w={w} h={8} r={2} tone={2} />
          </span>
        ))}
      </div>
    </section>
  )
}

export default function Expense() {
  return (
    <Stage<S>
      width={572}
      height={680}
      compact={{ below: 572, width: 358, height: 600 }}
      initial={START}
      poster={POSTER}
      script={script}
      play="once"
      cursor={{ at: { wide: { x: 520, y: 600 }, compact: { x: 330, y: 570 } }, style: 'touch', ripple: true }}
      className="bv"
    >
      {(s, _rect, layout) => (
        <Phone width={layout === 'compact' ? 302 : 360} frame="outline" status className="bv-phone">
          <div className="bv-sheet">
            <div className="bv-head">
              <span className="bv-title">쓴 돈 기록</span>
              <span className="bv-close">닫기</span>
            </div>

            <div className="bv-body">
              <section className="bv-sec">
                <Label>금액</Label>
                {/* A right-aligned amount steps left a digit at a time as it is typed, as the real input does */}
                <Field data-snap className="bv-amount" value={won(s.amount)} focused={s.focus} trailing={<span className="bv-unit">원</span>} />
              </section>

              <section className="bv-sec">
                <Label>거래처</Label>
                <Field className="bv-vendor" value={s.vendor ? PICK_VENDOR : ''} placeholder="거래처 이름" />
                <div className="bv-opts">
                  {VENDORS.map((v) => (
                    <Opt key={v} label={v} on={s.vendor && v === PICK_VENDOR} target={v === PICK_VENDOR ? 'vendor' : undefined} />
                  ))}
                </div>
              </section>

              <section className="bv-sec">
                <Label>종류</Label>
                <div className="bv-opts">
                  {KINDS.map((k, i) => (
                    <Opt key={k} label={k} on={s.kind && i === 0} />
                  ))}
                </div>
              </section>

              <Collapse open={s.items}>
                <section className="bv-sec">
                  <Label>품목(누른 만큼 건수)</Label>
                  <div className="bv-opts">
                    {ITEMS.map((it, i) =>
                      i === 0 ? (
                        <span key={it} className="bv-pair">
                          <Opt label={s.count ? `${it} ${s.count}` : it} on={s.count > 0} target="item" />
                          <span className="bv-minus" data-open={s.count > 0 || undefined}>
                            <Button className="bv-opt bv-opt--minus" aria-label="1건 빼기">
                              <Minus size={16} strokeWidth={2} aria-hidden />
                            </Button>
                          </span>
                        </span>
                      ) : (
                        <Opt key={it} label={it} />
                      ),
                    )}
                  </div>
                </section>
              </Collapse>

              <Filler label={30} cells={[44, 70, 34]} />
              <Filler label={30} cells={[34, 82, 56]} />
              <Filler label={30} cells={[60, 48, 66]} />
            </div>
          </div>
        </Phone>
      )}
    </Stage>
  )
}
