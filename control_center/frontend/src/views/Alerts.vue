<template>
  <div class="space-y-4">
    <div class="bg-white rounded-xl border border-gray-200 p-6">
      <h2 class="font-semibold text-gray-900 mb-4">Send Test Alert</h2>
      <form @submit.prevent="sendTest" class="flex items-end gap-3">
        <div class="flex-1">
          <label class="form-label">Recipient Email</label>
          <input v-model="testEmail" type="email" class="form-input" placeholder="you@example.com" />
        </div>
        <button type="submit" :disabled="sending" class="btn-primary">
          {{ sending ? 'Sending…' : 'Send Test' }}
        </button>
      </form>
      <p v-if="testResult" class="mt-3 text-sm" :class="testResult.ok ? 'text-green-600' : 'text-red-500'">
        {{ testResult.ok ? `✓ Sent to ${testResult.sent_to}` : `✗ ${testResult.detail}` }}
      </p>
    </div>

    <!-- Config hints -->
    <div class="bg-white rounded-xl border border-gray-200 p-6 space-y-3">
      <h2 class="font-semibold text-gray-900">Alert Configuration</h2>
      <p class="text-sm text-gray-500">
        Configure SMTP and Slack in your <code class="bg-gray-100 px-1 rounded">.env.control</code> file.
        Expiry alerts fire automatically daily via Celery beat — 7 days and 1 day before expiry.
      </p>
      <div class="grid grid-cols-1 md:grid-cols-2 gap-3 mt-4">
        <div class="bg-gray-50 rounded-lg p-4 text-sm">
          <p class="font-medium text-gray-700 mb-2">Email (SMTP)</p>
          <code class="text-xs text-gray-500 block leading-6">
            SMTP_HOST=smtp.sendgrid.net<br>
            SMTP_PORT=587<br>
            SMTP_USER=apikey<br>
            SMTP_PASSWORD=SG.xxx<br>
            ALERT_FROM_EMAIL=alerts@styloworld.io
          </code>
        </div>
        <div class="bg-gray-50 rounded-lg p-4 text-sm">
          <p class="font-medium text-gray-700 mb-2">Slack</p>
          <code class="text-xs text-gray-500 block leading-6">
            SLACK_WEBHOOK_URL=https://hooks.slack.com/...
          </code>
          <p class="text-xs text-gray-400 mt-2">Get a webhook URL from your Slack app settings → Incoming Webhooks.</p>
        </div>
      </div>
    </div>

    <!-- Recent alert log (placeholder — populated by Sprint 4) -->
    <div class="bg-white rounded-xl border border-gray-200">
      <div class="px-5 py-4 border-b border-gray-100">
        <h2 class="font-semibold text-gray-900 text-sm">Alert History</h2>
      </div>
      <div class="px-5 py-10 text-center text-sm text-gray-400">
        Alert history tracking will appear here once Celery expiry tasks run.
      </div>
    </div>
  </div>
</template>

<script setup>
/**
 * Alerts.vue — alert configuration reference and manual test sender.
 *
 * Sections:
 *   Test Alert panel — send a test email to verify SMTP is configured correctly
 *   Config hints     — display the required .env.control keys for SMTP and Slack
 *   Alert History    — placeholder; full alert log DB tracking added in Sprint 4
 *
 * Automated license expiry alerts are sent by tasks/check_expiry.py (Celery).
 * This page only provides manual testing and configuration guidance.
 */
import { ref } from 'vue'
import api from '../api'

const testEmail = ref('')
const sending = ref(false)
const testResult = ref(null)

async function sendTest() {
  sending.value = true
  testResult.value = null
  try {
    const { data } = await api.post('/api/alerts/test', { email: testEmail.value })
    testResult.value = data
  } catch (e) {
    testResult.value = { ok: false, detail: e.response?.data?.detail || 'Request failed' }
  } finally {
    sending.value = false
  }
}
</script>

<style>
.form-label { @apply block text-sm font-medium text-gray-700 mb-1; }
.form-input { @apply w-full border border-gray-300 rounded-lg px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent; }
.btn-primary { @apply bg-brand-500 hover:bg-brand-600 text-white text-sm font-medium px-4 py-2 rounded-lg transition-colors disabled:opacity-60; }
</style>
