import { StrictMode, useEffect, useState, type ComponentType } from 'react'
import { createRoot } from 'react-dom/client'
import Expense from '../examples/bv-expense'  // expense/ is copied to examples/bv-expense/
import Payment from '../examples/bv-payment'  // payment/ is copied to examples/bv-payment/

// Mounts the ledger demos into the staff guide. Each figure's replay button
// sits in its caption, outside the stage, and remounts that demo at its story
// boundary (kit.md, Explicit replay).
function WithReplay({ Demo, button }: { Demo: ComponentType; button: HTMLElement | null }) {
  const [run, setRun] = useState(0)
  useEffect(() => {
    if (!button) return
    const replay = () => setRun((n) => n + 1)
    button.addEventListener('click', replay)
    return () => button.removeEventListener('click', replay)
  }, [button])
  return <Demo key={run} />
}

const DEMOS: [string, ComponentType][] = [
  ['bv-expense', Expense],
  ['bv-payment', Payment],
]

function mount() {
  for (const [id, Demo] of DEMOS) {
    const host = document.getElementById(`${id}-demo`)
    if (!host) continue
    createRoot(host).render(
      <StrictMode>
        <WithReplay Demo={Demo} button={document.getElementById(`${id}-replay`)} />
      </StrictMode>,
    )
  }
}

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount)
else mount()
