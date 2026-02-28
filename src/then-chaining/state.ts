import type { ThenEntry } from "./frontmatter.js"

export interface ChainFrame {
  /** The full then sequence for this command invocation */
  entries: ThenEntry[]
  /** Current index into the entries array (0-based) */
  currentIndex: number
  /** The command name that originated this chain (for logging) */
  originCommand: string
}

export interface ChainState {
  /** Stack of chain frames -- innermost (deepest nested) chain is last */
  stack: ChainFrame[]
}

export class ChainStateManager {
  private chains: Map<string, ChainState> = new Map()
  private maxDepth: number

  constructor(maxDepth: number = 10) {
    this.maxDepth = maxDepth
  }

  /**
   * Push a new chain frame onto the stack for a session.
   * Returns false if max depth would be exceeded (recursion guard).
   */
  pushChain(
    sessionID: string,
    entries: ThenEntry[],
    originCommand: string,
  ): boolean {
    let state = this.chains.get(sessionID)
    if (!state) {
      state = { stack: [] }
      this.chains.set(sessionID, state)
    }

    if (state.stack.length >= this.maxDepth) {
      return false
    }

    state.stack.push({
      entries,
      currentIndex: 0,
      originCommand,
    })

    return true
  }

  /**
   * Get the next entry to execute for a session.
   * Returns undefined if no active chain or chain is exhausted.
   * Advances the current index.
   */
  advance(sessionID: string): ThenEntry | undefined {
    const state = this.chains.get(sessionID)
    if (!state || state.stack.length === 0) {
      return undefined
    }

    const frame = state.stack[state.stack.length - 1]
    if (frame.currentIndex >= frame.entries.length) {
      return undefined
    }

    const entry = frame.entries[frame.currentIndex]
    frame.currentIndex++
    return entry
  }

  /**
   * Pop the current (innermost) chain frame.
   * Called when a nested chain completes.
   * If the stack is empty after popping, cleans up the session entry.
   */
  popChain(sessionID: string): void {
    const state = this.chains.get(sessionID)
    if (!state) {
      return
    }

    state.stack.pop()

    if (state.stack.length === 0) {
      this.chains.delete(sessionID)
    }
  }

  /**
   * Check if a session has an active chain.
   */
  hasActiveChain(sessionID: string): boolean {
    const state = this.chains.get(sessionID)
    if (!state || state.stack.length === 0) {
      return false
    }
    // Check if any frame still has remaining entries to process
    return state.stack.some(
      (frame) => frame.currentIndex < frame.entries.length,
    )
  }

  /**
   * Get the current depth (stack size) for a session.
   */
  currentDepth(sessionID: string): number {
    const state = this.chains.get(sessionID)
    if (!state) {
      return 0
    }
    return state.stack.length
  }

  /**
   * Interrupt and discard all chains for a session.
   * Called when user manually invokes a command mid-chain,
   * or when the session ends.
   */
  interrupt(sessionID: string): void {
    this.chains.delete(sessionID)
  }
}
