import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import path from 'node:path'
import test from 'node:test'
import { compileScript, compileTemplate, parse } from '@vue/compiler-sfc'

const appPath = path.resolve(process.cwd(), 'src/App.vue')

test('App.vue parses and compiles without SFC errors', async () => {
  const source = await readFile(appPath, 'utf8')
  const { descriptor, errors } = parse(source, { filename: appPath })

  assert.equal(errors.length, 0, `SFC parse errors: ${JSON.stringify(errors)}`)
  assert.ok(descriptor.template, 'template block is required')

  const script = compileScript(descriptor, { id: 'app-test' })
  assert.match(script.content, /useDashboardStore/, 'App should use centralized dashboard state manager')

  const templateResult = compileTemplate({
    filename: appPath,
    id: 'app-test',
    source: descriptor.template.content,
    compilerOptions: {
      bindingMetadata: script.bindings,
    },
  })

  assert.equal(templateResult.errors.length, 0, `Template compile errors: ${JSON.stringify(templateResult.errors)}`)
})

test('App.vue template is composed from views and modal components', async () => {
  const source = await readFile(appPath, 'utf8')
  const { descriptor } = parse(source, { filename: appPath })
  const template = descriptor.template?.content || ''

  const requiredTags = ['DashboardSidebarView', 'DashboardMainView', 'LanHostModal', 'IframeModal', 'ItemEditorModal']

  for (const tag of requiredTags) {
    assert.ok(template.includes(`<${tag}`), `Expected <${tag}> in App template`)
  }
})
