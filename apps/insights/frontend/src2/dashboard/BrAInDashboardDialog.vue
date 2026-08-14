<script setup lang="ts">
import { Button, Dialog, FormControl } from 'frappe-ui'
import { Loader2, Sparkles } from 'lucide-vue-next'
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { __ } from '../translation'

const show = defineModel<boolean>({ default: false })
const router = useRouter()

const prompt = ref('')
const statusText = ref('')
const isLoading = ref(false)
const errorText = ref('')

async function createDashboard() {
	if (!prompt.value.trim() || isLoading.value) return

	isLoading.value = true
	statusText.value = __('Thinking…')
	errorText.value = ''

	const context = JSON.stringify({
		insights_ctx: { page: 'dashboard_list' },
		route: ['insights', 'dashboards'],
	})

	const csrfToken =
		(window as any).csrf_token ||
		document.cookie
			.split('; ')
			.find((c) => c.startsWith('csrf_token='))
			?.split('=')[1] ||
		''

	try {
		const response = await fetch('/api/method/brain.api.chat.send_stream', {
			method: 'POST',
			headers: {
				'Content-Type': 'application/x-www-form-urlencoded',
				'X-Frappe-CSRF-Token': csrfToken,
			},
			body: new URLSearchParams({
				message: prompt.value,
				history: '[]',
				context,
			}),
		})

		if (!response.ok) {
			throw new Error(__('brAIn request failed. Is the brAIn app enabled?'))
		}
		if (!response.body) {
			throw new Error(__('No response stream received'))
		}

		const reader = response.body.getReader()
		const decoder = new TextDecoder()
		let buffer = ''

		while (true) {
			const { done, value } = await reader.read()
			if (done) break
			buffer += decoder.decode(value, { stream: true })
			const lines = buffer.split('\n')
			buffer = lines.pop() || ''

			for (const line of lines) {
				if (!line.startsWith('data: ')) continue
				const json = line.slice(6).trim()
				if (!json) continue

				let event: any
				try {
					event = JSON.parse(json)
				} catch {
					continue
				}

				if (event.type === 'tool') {
					statusText.value = event.label || __('Working…')
				} else if (event.type === 'done') {
					const actions: any[] = event.actions || []
					const navAction = actions.find((a) => a.type === 'open_insights_dashboard')
					if (navAction?.workbook && navAction?.dashboard) {
						show.value = false
						prompt.value = ''
						router.push(`/workbook/${navAction.workbook}/dashboard/${navAction.dashboard}`)
					} else {
						errorText.value =
							event.message ||
							__('Dashboard could not be created. Try rephrasing your request.')
					}
				} else if (event.type === 'error') {
					errorText.value = event.message || __('An unexpected error occurred')
				}
			}
		}
	} catch (e: any) {
		errorText.value = e.message || __('Unexpected error')
	} finally {
		isLoading.value = false
		if (!errorText.value) statusText.value = ''
	}
}

function handleClose() {
	if (!isLoading.value) {
		show.value = false
		errorText.value = ''
	}
}
</script>

<template>
	<Dialog
		:modelValue="show"
		@update:modelValue="handleClose"
		:options="{
			title: __('Create Dashboard with brAIn'),
			size: 'lg',
		}"
	>
		<template #body-content>
			<div class="flex flex-col gap-4">
				<p class="text-sm text-gray-600">
					{{
						__(
							'Describe the dashboard you want in plain language. brAIn will create the queries, charts, and layout automatically.',
						)
					}}
				</p>

				<FormControl
					type="textarea"
					:placeholder="
						__(
							'e.g. Show me monthly revenue as a bar chart, total invoices this year as a number, and top 5 customers by sales as a pie chart',
						)
					"
					v-model="prompt"
					:rows="4"
					:disabled="isLoading"
					@keydown.enter.ctrl="createDashboard"
				/>

				<!-- Streaming status -->
				<div v-if="isLoading" class="flex items-center gap-2 text-sm text-gray-500">
					<Loader2 class="h-4 w-4 animate-spin" />
					<span>{{ statusText }}</span>
				</div>

				<!-- Error -->
				<p v-if="errorText" class="rounded-md bg-red-50 px-3 py-2 text-sm text-red-600">
					{{ errorText }}
				</p>
			</div>
		</template>

		<template #actions>
			<div class="flex items-center justify-end gap-2">
				<Button variant="subtle" @click="handleClose" :disabled="isLoading">
					{{ __('Cancel') }}
				</Button>
				<Button
					variant="solid"
					:loading="isLoading"
					:disabled="!prompt.trim() || isLoading"
					@click="createDashboard"
					class="gap-1.5"
				>
					<template #prefix>
						<Sparkles class="h-3.5 w-3.5" />
					</template>
					{{ __('Create with brAIn') }}
				</Button>
			</div>
		</template>
	</Dialog>
</template>
