<template>
  <span
    class="inline-flex items-center px-2 py-0.5 rounded-full text-xs font-medium"
    :class="classes[status] || 'bg-gray-100 text-gray-700'"
  >
    {{ status }}
  </span>
</template>

<script setup>
/**
 * StatusBadge.vue — colored pill badge for status values.
 *
 * Props:
 *   status (String) — any of: active, provisioning, suspended, terminated,
 *                     running, success, failed, revoked, expired
 *
 * Unknown status values fall back to a neutral gray badge.
 * Used in site tables, license tables, and deploy log rows.
 */
defineProps({ status: String })

const classes = {
  active: 'bg-green-100 text-green-700',
  provisioning: 'bg-blue-100 text-blue-700',
  suspended: 'bg-yellow-100 text-yellow-700',
  terminated: 'bg-red-100 text-red-600',
  running: 'bg-blue-100 text-blue-700',
  success: 'bg-green-100 text-green-700',
  failed: 'bg-red-100 text-red-600',
  revoked: 'bg-red-100 text-red-600',
  expired: 'bg-gray-100 text-gray-500',
}
</script>
