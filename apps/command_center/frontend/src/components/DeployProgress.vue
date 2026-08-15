<template>
  <Dialog v-model="show" :options="{ title, size: 'xl' }">
    <template #body-content>
      <div class="space-y-3">
        <div v-if="overall === 'in_progress'" class="flex items-center gap-2 text-sm text-ink-gray-6">
          <span class="inline-block h-2 w-2 animate-pulse rounded-full bg-blue-500"></span>
          Running…
        </div>
        <div v-else-if="overall === 'done'" class="flex items-center gap-2 text-sm text-ink-green-3">
          <span class="inline-block h-2 w-2 rounded-full bg-green-500"></span>
          Completed successfully
        </div>
        <div v-else-if="overall === 'failed'" class="flex items-center gap-2 text-sm font-medium text-ink-red-4">
          <span class="inline-block h-2 w-2 rounded-full bg-red-500"></span>
          Failed — see the failing step below
        </div>

        <ul class="space-y-1">
          <li v-for="s in steps" :key="s.step + s.timestamp" class="flex items-start gap-2 text-sm">
            <span v-if="s.success" class="mt-0.5 text-ink-green-3">✓</span>
            <span v-else class="mt-0.5 text-ink-red-4">✗</span>
            <div class="flex-1">
              <div :class="s.success ? '' : 'font-medium text-ink-red-4'">{{ s.step }}</div>
              <pre
                v-if="!s.success"
                class="mt-1 max-h-40 overflow-auto rounded bg-surface-gray-2 p-2 text-xs"
              >{{ s.output }}</pre>
            </div>
          </li>
          <li v-if="overall === 'in_progress'" class="flex items-center gap-2 text-sm text-ink-gray-5">
            <span class="mt-0.5">…</span>
            <span>waiting for next step</span>
          </li>
          <li v-if="!steps.length && overall === 'in_progress'" class="text-sm text-ink-gray-5">
            Queued — waiting for a worker to pick this up.
          </li>
        </ul>
      </div>
    </template>
  </Dialog>
</template>

<script setup>
import { ref, computed, watch, onUnmounted } from 'vue'
import { call } from 'frappe-ui'

const props = defineProps({
  modelValue: Boolean,
  title: { type: String, default: 'Deployment Progress' },
  site: String,
  siteRequest: String,
  since: String,
})
const emit = defineEmits(['update:modelValue'])

const show = computed({
  get: () => props.modelValue,
  set: (v) => emit('update:modelValue', v),
})

const steps = ref([])
const overall = ref('in_progress')
let pollTimer = null

async function poll() {
  const result = await call('command_center.api.deploy.get_deploy_progress', {
    site: props.site,
    site_request: props.siteRequest,
    since: props.since,
  })
  steps.value = result.steps
  overall.value = result.overall
  if (overall.value !== 'in_progress' && pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
}

watch(
  () => props.modelValue,
  (open) => {
    if (open) {
      steps.value = []
      overall.value = 'in_progress'
      poll()
      pollTimer = setInterval(poll, 2000)
    } else if (pollTimer) {
      clearInterval(pollTimer)
      pollTimer = null
    }
  },
)

onUnmounted(() => {
  if (pollTimer) clearInterval(pollTimer)
})
</script>
