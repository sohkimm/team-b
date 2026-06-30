import { cp, mkdir, rm } from 'node:fs/promises'
import { join, resolve } from 'node:path'

const root = resolve(import.meta.dirname, '..')
const repo = resolve(root, '..')
const source = join(root, 'dist')
const output = join(repo, 'dist')

await rm(output, { recursive: true, force: true })
await mkdir(join(output, 'client'), { recursive: true })
await mkdir(join(output, 'server'), { recursive: true })
await mkdir(join(output, '.openai'), { recursive: true })

await cp(source, join(output, 'client'), { recursive: true })
await cp(join(root, 'worker', 'index.js'), join(output, 'server', 'index.js'))
await cp(join(repo, '.openai', 'hosting.json'), join(output, '.openai', 'hosting.json'))
