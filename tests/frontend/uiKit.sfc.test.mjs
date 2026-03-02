import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import path from 'node:path'
import test from 'node:test'
import { pathToFileURL } from 'node:url'

const uiKitSfcPaths = [
  'src/pages/ui-showcase/UiShowcasePage.vue',
  'src/views/ui-showcase/UiPrimitivesDemoView.vue',
  'src/views/ui-showcase/UiShowcaseView.vue',
  'src/views/ui-showcase/components/UiNodeTree.vue',
  'src/views/ui-showcase/components/UiShowcaseNode.vue',
  'src/views/ui-showcase/components/UiSidebarDemoTree.vue',
  'src/views/ui-showcase/sections/UiKitDataSection.vue',
  'src/views/ui-showcase/sections/UiKitFormSection.vue',
  'src/views/ui-showcase/sections/UiKitHtmlFormCard.vue',
  'src/views/ui-showcase/sections/UiKitHtmlSection.vue',
  'src/views/ui-showcase/sections/UiKitLayoutSection.vue',
  'src/views/ui-showcase/sections/UiKitOverlaySection.vue',
]

let compiler = null

async function loadCompiler() {
  if (compiler) return compiler
  const compilerPath = path.resolve(process.cwd(), 'node_modules/@vue/compiler-sfc/dist/compiler-sfc.cjs.js')
  const imported = await import(pathToFileURL(compilerPath).href)
  compiler = imported.default || imported
  return compiler
}

test('ui-kit SFC files parse and compile without errors', async () => {
  const { compileScript, compileTemplate, parse } = await loadCompiler()

  for (const relativePath of uiKitSfcPaths) {
    const absolutePath = path.resolve(process.cwd(), relativePath)
    const source = await readFile(absolutePath, 'utf8')
    const { descriptor, errors } = parse(source, { filename: absolutePath })

    assert.equal(errors.length, 0, `SFC parse errors in ${relativePath}: ${JSON.stringify(errors)}`)
    assert.ok(descriptor.template, `template block is required in ${relativePath}`)

    const script = compileScript(descriptor, { id: `uikit-${relativePath}` })
    const templateResult = compileTemplate({
      filename: absolutePath,
      id: `uikit-${relativePath}`,
      source: descriptor.template.content,
      compilerOptions: {
        bindingMetadata: script.bindings,
      },
    })

    assert.equal(
      templateResult.errors.length,
      0,
      `template compile errors in ${relativePath}: ${JSON.stringify(templateResult.errors)}`,
    )
  }
})
