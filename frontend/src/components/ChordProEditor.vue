<script setup lang="ts">
import { ref, computed } from 'vue'

const props = defineProps<{
  modelValue: string
}>()
const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

const editorEl = ref<HTMLDivElement>()

function onInput(e: Event) {
  const target = e.target as HTMLTextAreaElement
  emit('update:modelValue', target.value)
}

interface ChordProError {
  line: number
  message: string
}

const errors = computed(() => {
  const errs: ChordProError[] = []
  const lines = props.modelValue.split('\n')
  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    const stripped = line.trim()
    if (!stripped) continue
    if (stripped.startsWith('{') && !stripped.endsWith('}')) {
      errs.push({ line: i + 1, message: 'Unclosed tag' })
    }
    const chordMatches = line.match(/\[([^\]]*)\]/g)
    if (chordMatches) {
      for (const m of chordMatches) {
        const chord = m.slice(1, -1).trim()
        if (chord && !/^[A-G][#b]?(m|min|maj|dim|aug|sus|add|[0-9])*$/i.test(chord)) {
          errs.push({ line: i + 1, message: `Unknown chord: ${chord}` })
        }
      }
    }
  }
  return errs
})

const highlighted = computed(() => {
  const lines = props.modelValue.split('\n')
  return lines.map(line => {
    const escaped = line
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
    let lastIdx = 0
    const parts: string[] = []
    const matches = [...escaped.matchAll(/\{[^}]+\}|\[[^\]]*\]/g)]
    if (matches.length === 0) return `<span>${escaped}</span>`
    for (const m of matches) {
      if (m.index! > lastIdx) {
        parts.push(`<span>${escaped.slice(lastIdx, m.index)}</span>`)
      }
      const token = m[0]
      if (token.startsWith('{')) {
        parts.push(`<span class="hl-tag">${token}</span>`)
      } else {
        parts.push(`<span class="hl-chord">${token}</span>`)
      }
      lastIdx = m.index! + token.length
    }
    if (lastIdx < escaped.length) {
      parts.push(`<span>${escaped.slice(lastIdx)}</span>`)
    }
    return parts.join('')
  }).join('\n')
})

function scrollHighlighter(e: Event) {
  const sync = (e.target as HTMLElement)?.closest('.editor-wrapper')?.querySelector('.highlighter') as HTMLElement
  if (sync) {
    sync.scrollTop = (e.target as HTMLElement).scrollTop
    sync.scrollLeft = (e.target as HTMLElement).scrollLeft
  }
}
</script>

<template>
  <div class="editor-wrapper">
    <div class="editor-stack">
      <pre class="highlighter" aria-hidden="true"><code v-html="highlighted"></code></pre>
      <textarea
        :value="modelValue"
        @input="onInput"
        @scroll="scrollHighlighter"
        class="editor-textarea"
        placeholder="{title: Song Title}
{artist: Artist Name}
{capo: 2}
{key: G}

{start_of_verse}
[Am]Hello [C]world
[G]This is a [D]song
{end_of_verse}

{start_of_chorus: Chorus}
[C]Sing a-[G]long with [Am]me
{end_of_chorus}"
        spellcheck="false"
      ></textarea>
    </div>
    <div v-if="errors.length" class="errors">
      <div v-for="err in errors" :key="err.line" class="error-item">
        Line {{ err.line }}: {{ err.message }}
      </div>
    </div>
    <div class="editor-hint">
      ChordPro format: <code>[Chord]lyrics</code>. Tags: <code>{title:}</code>, <code>{artist:}</code>, <code>{start_of_verse}</code>, <code>{start_of_chorus}</code>
    </div>
  </div>
</template>

<style scoped>
.editor-wrapper {
  width: 100%;
}
.editor-stack {
  position: relative;
  min-height: 300px;
}
.highlighter,
.editor-textarea {
  width: 100%;
  min-height: 300px;
  font-family: 'Courier New', Courier, monospace;
  font-size: 0.95rem;
  line-height: 1.6;
  padding: 0.75rem;
  border: 1px solid var(--border);
  border-radius: 6px;
  white-space: pre-wrap;
  word-wrap: break-word;
  overflow-wrap: break-word;
}
.highlighter {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  margin: 0;
  pointer-events: none;
  background: var(--surface);
  color: var(--text);
  overflow: hidden;
}
.highlighter code {
  font-family: inherit;
  font-size: inherit;
  line-height: inherit;
}
.editor-textarea {
  position: relative;
  z-index: 1;
  background: transparent;
  color: transparent;
  caret-color: var(--text);
  resize: vertical;
  border-color: transparent;
}
.editor-textarea:focus {
  outline: none;
  border-color: var(--accent);
}
.editor-textarea::placeholder {
  color: transparent;
}
.editor-textarea:focus + .highlighter,
.editor-textarea:focus ~ .highlighter {
  border-color: var(--accent);
}
.highlighter :deep(.hl-tag) {
  color: #6a9955;
  font-weight: 600;
}
.highlighter :deep(.hl-chord) {
  color: var(--accent);
  font-weight: 700;
}
.errors {
  margin-top: 0.5rem;
  padding: 0.5rem;
  background: rgba(231, 76, 60, 0.1);
  border: 1px solid var(--danger);
  border-radius: 4px;
}
.error-item {
  color: var(--danger);
  font-size: 0.8rem;
  font-family: monospace;
}
.editor-hint {
  font-size: 0.8rem;
  color: var(--text-muted);
  margin-top: 0.5rem;
}
.editor-hint code {
  background: var(--surface);
  padding: 0.1rem 0.3rem;
  border-radius: 3px;
}
</style>
