<template>
  <div v-if="site.doc" class="space-y-4">
    <h1 class="text-2xl font-semibold">{{ site.doc.sitename }}</h1>
    <div class="grid grid-cols-2 gap-4 text-sm sm:grid-cols-3">
      <div><span class="text-ink-gray-5">Client:</span> {{ site.doc.client_name }}</div>
      <div><span class="text-ink-gray-5">Server:</span> {{ site.doc.server }}</div>
      <div><span class="text-ink-gray-5">Status:</span> {{ site.doc.status }}</div>
      <div><span class="text-ink-gray-5">License:</span> {{ site.doc.license || '—' }}</div>
    </div>
    <div v-if="session.isSuperAdmin" class="flex justify-end gap-2">
      <Button variant="outline" size="sm" @click="openPasswordDialog">
        Change Admin Password
      </Button>
      <Button variant="outline" theme="red" size="sm" @click="openDeleteDialog">
        Delete Site
      </Button>
    </div>
    <div>
      <div class="mb-2 flex items-center justify-between">
        <div class="text-sm font-medium text-ink-gray-5">Installed Modules</div>
        <Button v-if="session.isSuperAdmin" variant="outline" size="sm" @click="openInstallDialog">
          Install Module
        </Button>
      </div>
      <table class="w-full text-sm">
        <tbody>
          <tr v-for="m in site.doc.modules" :key="m.name" class="border-b">
            <td class="py-1">{{ m.module_key }}</td>
            <td class="py-1 text-ink-gray-5">{{ m.installed_on }}</td>
          </tr>
        </tbody>
      </table>
    </div>

    <Dialog v-model="showInstallDialog" :options="{ title: 'Install Module' }">
      <template #body-content>
        <div class="space-y-3">
          <FormControl
            label="Module"
            type="select"
            v-model="moduleToInstall"
            :options="availableModules"
          />
          <p class="text-xs text-ink-gray-5">
            Runs in the background over SSH — installs the app(s), runs post-install, and
            restarts the site's web service. Check the Dashboard for failures.
          </p>
          <Button variant="solid" @click="installModule">Start Install</Button>
        </div>
      </template>
    </Dialog>

    <Dialog v-model="showPasswordDialog" :options="{ title: 'Change Admin Password' }">
      <template #body-content>
        <div class="space-y-3">
          <p class="text-xs text-ink-gray-5">
            Changes the Administrator login on {{ props.siteName }} itself (over SSH via
            `bench set-admin-password`) — takes effect immediately.
          </p>
          <FormControl label="New Password" type="password" v-model="newAdminPassword" />
          <p v-if="passwordError" class="text-xs text-ink-red-4">{{ passwordError }}</p>
          <Button variant="solid" :loading="changingPassword" @click="changeAdminPassword">
            Change Password
          </Button>
        </div>
      </template>
    </Dialog>

    <Dialog v-model="showDeleteDialog" :options="{ title: 'Delete Site — Irreversible' }">
      <template #body-content>
        <div class="space-y-3">
          <p class="text-sm text-ink-red-4">
            This drops the site's database and files on {{ site.doc.server }}. There is no
            undo. Type the site name to confirm.
          </p>
          <FormControl label="Site name" v-model="deleteConfirmText" :placeholder="props.siteName" />
          <FormControl
            type="checkbox"
            label="Take a backup first and store it in Command Center (recommended)"
            v-model="deleteTakeBackup"
          />
          <Button
            variant="solid"
            theme="red"
            :disabled="deleteConfirmText !== props.siteName"
            @click="deleteSite"
          >
            Delete {{ props.siteName }}
          </Button>
        </div>
      </template>
    </Dialog>

    <DeployProgress
      v-model="showProgress"
      :title="progressTitle"
      :site="props.siteName"
      :since="progressSince"
      @update:model-value="
        (open) => {
          if (open) return
          if (deleted) router.push('/command-center/sites')
          else site.reload()
        }
      "
    />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { createDocumentResource, createResource, call } from 'frappe-ui'
import { useRouter } from 'vue-router'
import { sessionStore } from '@/stores/session'
import DeployProgress from '@/components/DeployProgress.vue'

const props = defineProps({ siteName: String })
const session = sessionStore()
const router = useRouter()

const site = createDocumentResource({
  doctype: 'Site',
  name: props.siteName,
  auto: true,
})

const allModules = createResource({
  url: 'command_center.module_map.get_module_choices',
  auto: true,
})

const showInstallDialog = ref(false)
const moduleToInstall = ref('')
const showProgress = ref(false)
const progressSince = ref(null)
const progressTitle = ref('Installing Module')

const showDeleteDialog = ref(false)
const deleteConfirmText = ref('')
const deleteTakeBackup = ref(true)
const deleted = ref(false)

const showPasswordDialog = ref(false)
const newAdminPassword = ref('')
const changingPassword = ref(false)
const passwordError = ref('')

function openPasswordDialog() {
  newAdminPassword.value = ''
  passwordError.value = ''
  showPasswordDialog.value = true
}

async function changeAdminPassword() {
  changingPassword.value = true
  passwordError.value = ''
  try {
    await call('command_center.api.sites.change_admin_password', {
      site: props.siteName,
      new_password: newAdminPassword.value,
    })
    showPasswordDialog.value = false
  } catch (e) {
    passwordError.value = e.messages?.join(', ') || e.message || 'Failed to change password'
  } finally {
    changingPassword.value = false
  }
}

function openDeleteDialog() {
  deleteConfirmText.value = ''
  deleteTakeBackup.value = true
  showDeleteDialog.value = true
}

async function deleteSite() {
  if (deleteConfirmText.value !== props.siteName) return
  progressSince.value = await call('command_center.api.deploy.get_server_time')
  progressTitle.value = 'Deleting Site'
  await call('command_center.api.sites.request_delete_site', {
    site: props.siteName,
    take_backup: deleteTakeBackup.value,
  })
  showDeleteDialog.value = false
  deleted.value = true
  showProgress.value = true
}

const availableModules = computed(() => {
  const installed = new Set((site.doc?.modules || []).map((m) => m.module_key))
  return (allModules.data || []).filter((m) => !installed.has(m))
})

function openInstallDialog() {
  moduleToInstall.value = availableModules.value[0] || ''
  showInstallDialog.value = true
}

async function installModule() {
  if (!moduleToInstall.value) return
  // Captured before enqueueing so get_deploy_progress can exclude this site's Deploy Log
  // history from any module installed before now.
  progressSince.value = await call('command_center.api.deploy.get_server_time')
  progressTitle.value = 'Installing Module'
  await call('command_center.api.deploy.request_add_module', {
    site: props.siteName,
    module_key: moduleToInstall.value,
  })
  showInstallDialog.value = false
  showProgress.value = true
}
</script>
