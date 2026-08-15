import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

export default defineConfig(async ({ mode }) => {
  const isDev = mode === 'development'
  const config = {
    plugins: [vue()],
    resolve: {
      alias: {
        '@': path.resolve(__dirname, 'src'),
      },
    },
    server: {
      fs: {
        allow: [path.resolve(__dirname, '..')],
      },
    },
  }

  const frappeui = await importFrappeUIPlugin(isDev, config)
  config.plugins.unshift(
    frappeui({
      frappeProxy: true,
      lucideIcons: true,
      jinjaBootData: true,
      buildConfig: {
        indexHtmlPath: '../command_center/www/command_center.html',
        emptyOutDir: true,
        sourcemap: true,
      },
    }),
  )

  return config
})

async function importFrappeUIPlugin(isDev, config) {
  if (isDev) {
    try {
      const fs = await import('node:fs')
      const localVitePluginPath = path.resolve(__dirname, '../frappe-ui/vite')
      if (fs.existsSync(localVitePluginPath)) {
        const module = await import('../frappe-ui/vite')
        config.resolve.alias = getAliases(config)
        return module.default
      }
    } catch {
      // fall through to npm package
    }
  }
  const module = await import('frappe-ui/vite')
  return module.default
}

function getAliases(config) {
  return {
    ...config.resolve.alias,
    'frappe-ui/tailwind': path.resolve(__dirname, '../frappe-ui/tailwind/preset.js'),
    'frappe-ui/style.css': path.resolve(__dirname, '../frappe-ui/src/style.css'),
    'frappe-ui/frappe': path.resolve(__dirname, '../frappe-ui/frappe/index.js'),
    'frappe-ui': path.resolve(__dirname, '../frappe-ui/src/index.ts'),
  }
}
