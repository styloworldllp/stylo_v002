<template>
  <Modal v-model="open" :title="`Deploy Log — ${action}`" size="lg">
    <div class="space-y-3">
      <div class="flex items-center gap-3">
        <StatusBadge :status="log?.status || 'running'" />
        <span class="text-xs text-gray-500" v-if="log?.started_at">
          Started {{ formatDate(log.started_at) }}
        </span>
        <span class="text-xs text-gray-500" v-if="log?.finished_at">
          · Finished {{ formatDate(log.finished_at) }}
        </span>
      </div>

      <pre
        class="bg-gray-900 text-green-400 text-xs rounded-lg p-4 h-72 overflow-y-auto font-mono whitespace-pre-wrap scrollbar-thin"
      >{{ log?.log_output || 'Waiting for output…' }}</pre>

      <p v-if="log?.status === 'running'" class="text-xs text-gray-500 flex items-center gap-1">
        <span class="animate-pulse">⏳</span> Operation in progress — refreshing every 3s
      </p>
    </div>
  </Modal>
</template>

<script setup>
import { onUnmounted, ref, watch } from 'vue'
import api from '../api'
/**
 * DeployLogModal.vue — live-updating deploy log viewer.
 *
 * Props:
 *   modelValue (Boolean) — v-model; open/close the modal
 *   logId      (Number)  — ID of the DeployLog record to poll
 *   action     (String)  — action name shown in the modal title
 *
 * Behavior:
 *   When opened with a logId, starts polling GET /api/deploy/logs/{id}
 *   every 3 seconds.  Stops polling when log.status changes from "running"
 *   to "success" or "failed".  Polling is also stopped when the modal is
 *   closed or the component is unmounted.
 *
 *   The log output is rendered in a dark monospace <pre> block so SSH
 *   terminal output (including docker pull progress) is readable.
 */
import Modal from './Modal.vue'
import StatusBadge from './StatusBadge.vue'

const props = defineProps({
  modelValue: Boolean,
  logId: Number,
  action: String,
})
const emit = defineEmits(['update:modelValue'])

const open = ref(props.modelValue)
const log = ref(null)
let timer = null

watch(() => props.modelValue, (v) => {
  open.value = v
  if (v && props.logId) startPolling()
})
watch(open, (v) => {
  emit('update:modelValue', v)
  if (!v) stopPolling()
})

async function fetchLog() {
  try {
    const { data } = await api.get(`/api/deploy/logs/${props.logId}`)
    log.value = data
    if (data.status !== 'running') stopPolling()
  } catch {}
}

function startPolling() {
  log.value = null
  fetchLog()
  timer = setInterval(fetchLog, 3000)
}

function stopPolling() {
  clearInterval(timer)
  timer = null
}

onUnmounted(stopPolling)

function formatDate(d) {
  return new Date(d).toLocaleString()
}
</script>
