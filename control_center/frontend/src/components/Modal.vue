<template>
  <Teleport to="body">
    <div
      v-if="modelValue"
      class="fixed inset-0 z-50 flex items-center justify-center"
      @click.self="$emit('update:modelValue', false)"
    >
      <div class="absolute inset-0 bg-black/40"></div>
      <div
        class="relative bg-white rounded-xl shadow-xl w-full mx-4"
        :class="sizeClass"
      >
        <div class="flex items-center justify-between px-6 py-4 border-b border-gray-200">
          <h3 class="text-base font-semibold text-gray-900">{{ title }}</h3>
          <button
            @click="$emit('update:modelValue', false)"
            class="text-gray-400 hover:text-gray-600 text-xl leading-none"
          >×</button>
        </div>
        <div class="px-6 py-5">
          <slot />
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
/**
 * Modal.vue — reusable dialog overlay used throughout the app.
 *
 * Props:
 *   modelValue (Boolean) — v-model binding; controls visibility
 *   title      (String)  — dialog header text
 *   size       (String)  — 'sm' | 'md' | 'lg' | 'xl' (default 'md')
 *
 * Clicking the backdrop or the × button closes the modal by emitting
 * update:modelValue=false.  Content is provided via the default <slot>.
 *
 * Uses <Teleport to="body"> so the overlay is always on top of everything
 * regardless of where the component is placed in the DOM tree.
 */
import { computed } from 'vue'

const props = defineProps({
  modelValue: Boolean,
  title: String,
  size: { type: String, default: 'md' },
})
defineEmits(['update:modelValue'])

const sizeClass = computed(() => ({
  sm: 'max-w-sm',
  md: 'max-w-lg',
  lg: 'max-w-2xl',
  xl: 'max-w-4xl',
}[props.size]))
</script>
