<template>
  <div class="space-y-4">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-semibold">Site Requests</h1>
      <Button v-if="session.isAdmin" variant="solid" @click="showNewDialog = true">New Request</Button>
    </div>

    <table class="w-full text-sm">
      <thead>
        <tr class="border-b text-left text-ink-gray-5">
          <th class="py-2">Request</th>
          <th>Client</th>
          <th>Site</th>
          <th>Server</th>
          <th>Status</th>
          <th v-if="session.isSuperAdmin"></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="r in requests.data" :key="r.name" class="border-b">
          <td class="py-2">{{ r.name }}</td>
          <td>{{ r.client_name }}</td>
          <td>{{ r.sitename }}</td>
          <td>{{ r.server || '(auto)' }}</td>
          <td>
            <Badge
              :theme="statusTheme(r.status)"
              :class="hasLog(r.status) ? 'cursor-pointer' : ''"
              @click="hasLog(r.status) && viewLog(r.name)"
            >
              {{ r.status }}
            </Badge>
          </td>
          <td v-if="session.isSuperAdmin" class="space-x-2">
            <Button
              v-if="r.status === 'Pending Approval'"
              variant="solid"
              size="sm"
              @click="approve(r.name)"
            >
              Approve
            </Button>
            <Button
              v-if="r.status === 'Pending Approval'"
              variant="outline"
              size="sm"
              @click="reject(r.name)"
            >
              Reject
            </Button>
            <Button
              v-if="r.status === 'Failed'"
              variant="outline"
              size="sm"
              @click="retry(r.name)"
            >
              Retry
            </Button>
            <Button
              v-if="r.status === 'Deployed'"
              variant="outline"
              size="sm"
              @click="declareDemo(r.name)"
            >
              Declare Demo/POC
            </Button>
          </td>
        </tr>
      </tbody>
    </table>

    <Dialog v-model="showNewDialog" :options="{ title: 'New Site Request' }">
      <template #body-content>
        <div class="space-y-3">
          <FormControl label="Client Name" v-model="newRequest.client_name" />
          <FormControl label="Client Contact Email" v-model="newRequest.client_contact_email" />
          <FormControl label="Proposed Site Name" v-model="newRequest.sitename" />
          <FormControl label="Base Module" type="select" v-model="newRequest.base_module"
            :options="['crm', 'bms', 'hr', 'lms', 'desk', 'brain', 'insights']" />
          <div class="border-t pt-3 text-sm font-medium text-ink-gray-5">Setup Wizard</div>
          <FormControl
            label="Country"
            type="select"
            v-model="newRequest.country"
            :options="[{ label: 'Select...', value: '' }, ...countryOptions]"
          />
          <FormControl
            label="Currency"
            type="select"
            v-model="newRequest.currency"
            :options="[{ label: 'Select...', value: '' }, ...currencyOptions]"
          />
          <FormControl
            label="Timezone"
            type="select"
            v-model="newRequest.timezone"
            :options="[{ label: 'Select...', value: '' }, ...timezoneOptions]"
          />
          <FormControl
            label="Admin Password"
            type="password"
            v-model="newRequest.admin_password"
            placeholder="Leave blank for the default (Administrator / stylo123Admin)"
          />
          <Button variant="solid" @click="createRequest">Create</Button>
        </div>
      </template>
    </Dialog>

    <DeployProgress
      v-model="showProgress"
      title="Deploying Site"
      :site-request="progressRequestName"
      @update:model-value="(open) => !open && requests.reload()"
    />
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { createListResource, createResource, call } from 'frappe-ui'
import { sessionStore } from '@/stores/session'
import DeployProgress from '@/components/DeployProgress.vue'

const formChoices = createResource({
  url: 'command_center.api.site_request.get_form_choices',
  auto: true,
})
const countryOptions = computed(() => (formChoices.data?.countries || []).map((c) => ({ label: c, value: c })))
const currencyOptions = computed(() => (formChoices.data?.currencies || []).map((c) => ({ label: c, value: c })))
const timezoneOptions = computed(() => (formChoices.data?.timezones || []).map((t) => ({ label: t, value: t })))

const session = sessionStore()
const showNewDialog = ref(false)
const showProgress = ref(false)
const progressRequestName = ref('')
const newRequest = ref({
  client_name: '',
  client_contact_email: '',
  sitename: '',
  base_module: 'crm',
  country: '',
  currency: '',
  timezone: '',
  admin_password: '',
})

const requests = createListResource({
  doctype: 'Site Request',
  fields: ['name', 'client_name', 'sitename', 'server', 'status'],
  orderBy: 'modified desc',
  pageLength: 50,
  auto: true,
})

function hasLog(status) {
  return status !== 'Draft' && status !== 'Pending Approval'
}

function viewLog(name) {
  progressRequestName.value = name
  showProgress.value = true
}

function statusTheme(status) {
  return {
    Draft: 'gray',
    'Pending Approval': 'orange',
    Approved: 'blue',
    Rejected: 'red',
    Deployed: 'green',
    Failed: 'red',
  }[status] || 'gray'
}

async function createRequest() {
  await call('frappe.client.insert', {
    doc: { doctype: 'Site Request', ...newRequest.value },
  }).then((doc) =>
    call('command_center.api.site_request.submit_for_approval', { site_request: doc.name }),
  )
  showNewDialog.value = false
  newRequest.value = {
    client_name: '',
    client_contact_email: '',
    sitename: '',
    base_module: 'crm',
    country: '',
    currency: '',
    timezone: '',
    admin_password: '',
  }
  requests.reload()
}

async function approve(name) {
  await call('command_center.api.site_request.approve', { site_request: name })
  progressRequestName.value = name
  showProgress.value = true
  requests.reload()
}

async function reject(name) {
  await call('command_center.api.site_request.reject', { site_request: name })
  requests.reload()
}

async function retry(name) {
  await call('command_center.api.site_request.retry_deployment', { site_request: name })
  progressRequestName.value = name
  showProgress.value = true
  requests.reload()
}

async function declareDemo(name) {
  // Unlimited-access license for a client demo/POC site — no payment, no Stylo License
  // Request. Demo -> Active later is a simple status flip on the Stylo License record
  // itself (done from the Licenses page), not a new request.
  const result = await call('stylo_core.license_management.release_demo_license', { site_request: name })
  const sitename = requests.data.find((r) => r.name === name)?.sitename
  if (sitename && result?.site_api_key) {
    // Activate real login-time license enforcement on the site itself (was previously a
    // permanent no-op — see stylo_core/user_license.py's is_unlimited_access()/site_config).
    await call('command_center.api.sites.push_license_config', {
      sitename,
      site_api_key: result.site_api_key,
    })
  }
  requests.reload()
}
</script>
