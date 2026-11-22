import { StrictMode, useEffect, useState } from 'react'
import { createRoot } from 'react-dom/client'
import Expense from '../examples/bv-expense'  // expense/ is copied to examples/bv-expense/ in a Stageshow working copy

// Mounts the expense demo into the staff guide. The replay button sits in the
// figure's caption, outside the stage, and remounts the demo at its story
// boundary (kit.md, Explicit replay).
function WithReplay({ button }: { button: HTMLElement | null }) {
  const [run, setRun] = useState(0)
  useEffect(() => {
    if (!button) return
    const replay = () => setRun((n) => n + 1)
    button.addEventListener('click', replay)
    return () => button.removeEventListener('click', replay)
  }, [button])
  return <Expense key={run} />
}

function mount() {
  const host = document.getElementById('bv-expense-demo')
  if (!host) return
  createRoot(host).render(
    <StrictMode>
      <WithReplay button={document.getElementById('bv-expense-replay')} />
    </StrictMode>,
  )
}

if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', mount)
else mount()
