import { strict as assert } from 'node:assert'
import { mkdtempSync, mkdirSync, writeFileSync } from 'node:fs'
import { tmpdir } from 'node:os'
import { join } from 'node:path'
import { test } from 'node:test'
import { collectBlocks, extractBlocks, lintBlock } from './blocks.mjs'

test('extracts literal and listing blocks with their first source line', () => {
  const text = ['= Page', '', '[mermaid]', '....', 'flowchart LR', '  A --> B', '....', '', '[mermaid,format=svg]', '', '----', 'graph TD', '----'].join('\n')
  assert.deepEqual(extractBlocks(text), [
    { line: 5, src: 'flowchart LR\n  A --> B' },
    { line: 12, src: 'graph TD' }
  ])
})

test('ignores a [mermaid] attribute without a delimited block and other block styles', () => {
  assert.deepEqual(extractBlocks('[mermaid]\ntext\n\n[source,mermaid]\n----\nA\n----'), [])
})

test('flags tag-like text but not Mermaid arrows', () => {
  assert.deepEqual(lintBlock('classDiagram\n  A <|-- B\n  C <--> D\n  E <<->> F'), [])
  assert.deepEqual(lintBlock('flowchart LR\n  A["one<br>two<br/>three <b>bold</b>"]'), [])
  const problems = lintBlock('flowchart LR\n  A["write <timestamp>"]\n  B["&amp;lt;ok&amp;gt;"]\n  class X <<interface>>')
  assert.deepEqual(problems.map((p) => p.offset), [1, 3])
})

test('flags a single-escaped placeholder inside a label, accepts the double-escaped one', () => {
  assert.deepEqual(lintBlock('flowchart LR\n  A["meeting-&lt;timestamp&gt;"]').map((p) => p.offset), [1])
  assert.deepEqual(lintBlock('flowchart LR\n  A["meeting-&amp;lt;timestamp&amp;gt;"]'), [])
  assert.deepEqual(lintBlock('classDiagram\n  class Shape {\n    &lt;&lt;interface&gt;&gt;\n  }'), [])
})

test('collects blocks from pages and partials', () => {
  const dir = mkdtempSync(join(tmpdir(), 'mermaid-blocks-'))
  mkdirSync(join(dir, 'ROOT', 'partials'), { recursive: true })
  writeFileSync(join(dir, 'ROOT', 'partials', 'p.adoc'), '[mermaid]\n....\ngraph LR\n....\n')
  writeFileSync(join(dir, 'ROOT', 'skip.txt'), '[mermaid]\n....\ngraph LR\n....\n')
  const blocks = collectBlocks(dir)
  assert.equal(blocks.length, 1)
  assert.match(blocks[0].file, /p\.adoc$/)
})
