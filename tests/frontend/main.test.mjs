import assert from 'node:assert/strict'
import { readFile } from 'node:fs/promises'
import path from 'node:path'
import test from 'node:test'

const mainPath = path.resolve(process.cwd(), 'src/main.js')

test('main.js mounts App with global styles', async () => {
  const source = await readFile(mainPath, 'utf8')

  assert.match(source, /import\s+\{\s*createApp\s*\}\s+from\s+'vue'/)
  assert.match(source, /import\s+\{\s*MotionPlugin\s*\}\s+from\s+'@vueuse\/motion'/)
  assert.match(source, /import\s+App\s+from\s+'\.\/App\.vue'/)
  assert.match(source, /import\s+'\.\/styles\.scss'/)
  assert.match(source, /createApp\(App\)\.use\(MotionPlugin\)\.mount\('#app'\)/)
})
