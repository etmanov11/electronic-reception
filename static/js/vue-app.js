/**
 * Динамические компоненты интерфейса на базе Vue 3 (CDN).
 * Интегрирован с Django: обрабатывает CSRF, статус-трекер, уведомления, AJAX-запросы.
 */
document.addEventListener('DOMContentLoaded', () => {
    let statusTrackerState = null;
    let statusTrackerSteps = null;

    // 1. Инициализация статус-трекера (монтируется на <div id="status-tracker">)
    const trackerEl = document.getElementById('status-tracker');
    if (trackerEl) {
        const { createApp, ref, computed, onMounted } = Vue;

        createApp({
            setup() {
                const currentStatus = ref(trackerEl.dataset.currentStatus || 'new');
                statusTrackerState = currentStatus;
                const initialSteps = JSON.parse(trackerEl.dataset.workflowSteps || '[]');
                const steps = ref(initialSteps);
                statusTrackerSteps = steps;

                const progressIndex = computed(() => steps.value.findIndex(s => s.code === currentStatus.value));
                const currentStep = computed(() => steps.value.find(s => s.code === currentStatus.value));
                const isComplete = computed(() => Boolean(currentStep.value?.is_terminal));

                const getBadgeClass = (code) => `badge badge-status-${code}`;
                const isActive = (index, step) => {
                    if (index <= progressIndex.value && progressIndex.value !== -1) return true;
                    return step.code === currentStatus.value;
                };

                const syncFromResponse = (data) => {
                    if (data?.status) {
                        currentStatus.value = data.status;
                    }
                    if (Array.isArray(data?.workflow_steps)) {
                        steps.value = data.workflow_steps;
                    }
                };

                // Динамическое обновление статуса через API (для сотрудников)
                const fetchStatus = async () => {
                    const appealId = trackerEl.dataset.appealId;
                    if (!appealId) return;
                    try {
                        const res = await fetch(`/appeals/${appealId}/status-json/`, {
                            headers: { 'Accept': 'application/json' }
                        });
                        if (res.ok) {
                            const data = await res.json();
                            syncFromResponse(data);
                        }
                    } catch (err) {
                        console.warn('[Vue] Ошибка обновления статуса:', err);
                    }
                };

                onMounted(() => {
                    if (trackerEl.dataset.autoUpdate === 'true') {
                        setInterval(fetchStatus, 30000);
                    }
                });

                return { currentStatus, steps, getBadgeClass, isActive, isComplete };
            },
            template: `
                <div class="status-tracker mb-4 p-3 bg-white rounded shadow-sm" aria-label="Трекер статуса обращения">
                    <h6 class="fw-bold mb-3">Статус рассмотрения</h6>
                    <div class="d-flex flex-wrap gap-2 align-items-center">
                        <span v-for="(step, index) in steps" :key="step.code"
                              class="badge px-3 py-2 rounded-pill"
                              :class="getBadgeClass(step.code)"
                              :aria-current="isActive(index, step) ? 'step' : undefined"
                              :aria-hidden="!isActive(index, step)">
                            {{ step.label }}
                        </span>
                    </div>
                    <div class="mt-2 small text-success fw-semibold" v-if="isComplete">
                        Обращение завершено
                    </div>
                </div>
            `
        }).mount('#status-tracker');
    }

    // 2. Утилита получения CSRF-токена Django
    const getCSRFToken = () => {
        const token = document.querySelector('[name=csrfmiddlewaretoken]')?.value;
        if (token) return token;
        const match = document.cookie.match(/csrftoken=([^;]+)/);
        return match ? match[1] : '';
    };

    // 3. AJAX-отправка формы изменения статуса
    const statusForm = document.getElementById('status-change-form');
    if (statusForm) {
        statusForm.addEventListener('submit', async (e) => {
            e.preventDefault();
            const submitButton = statusForm.querySelector('button[type="submit"]');
            if (submitButton) {
                submitButton.disabled = true;
            }
            const formData = new FormData(statusForm);
            try {
                const res = await fetch(statusForm.action, {
                    method: 'POST',
                    body: formData,
                    headers: {
                        'X-Requested-With': 'XMLHttpRequest',
                        'X-CSRFToken': getCSRFToken(),
                        'Accept': 'application/json'
                    }
                });
                const contentType = res.headers.get('Content-Type') || '';
                const data = contentType.includes('application/json')
                    ? await res.json().catch(() => null)
                    : null;
                if (data?.success) {
                    const badge = document.getElementById('current-status-badge');
                    if (badge) {
                        badge.textContent = data.status_name;
                        badge.className = `badge badge-status-${data.status}`;
                    }
                    if (trackerEl) {
                        trackerEl.dataset.currentStatus = data.status;
                    }
                    if (statusTrackerState) {
                        statusTrackerState.value = data.status;
                    }
                    if (statusTrackerSteps && Array.isArray(data.workflow_steps)) {
                        statusTrackerSteps.value = data.workflow_steps;
                    }
                    const statusSelect = statusForm.querySelector('select[name="new_status"]');
                    if (statusSelect && Array.isArray(data.allowed_choices)) {
                        statusSelect.innerHTML = '';
                        if (data.allowed_choices.length) {
                            const placeholder = document.createElement('option');
                            placeholder.value = '';
                            placeholder.textContent = 'Выберите статус...';
                            statusSelect.appendChild(placeholder);
                            for (const choice of data.allowed_choices) {
                                const option = document.createElement('option');
                                option.value = choice.id;
                                option.textContent = choice.name;
                                statusSelect.appendChild(option);
                            }
                            statusSelect.value = '';
                        } else {
                            const option = document.createElement('option');
                            option.value = '';
                            option.textContent = 'Нет доступных переходов';
                            statusSelect.appendChild(option);
                            statusSelect.disabled = true;
                            if (submitButton) {
                                submitButton.disabled = true;
                            }
                        }
                    }
                    const commentField = statusForm.querySelector('textarea[name="comment"]');
                    if (commentField) {
                        commentField.value = '';
                    }
                    showToast('Статус успешно обновлён', 'success');
                } else if (res.redirected) {
                    window.location.href = res.url;
                } else if (res.ok && !data) {
                    window.location.reload();
                } else {
                    showToast(data?.message || `Ошибка обновления (HTTP ${res.status})`, 'danger');
                }
            } catch (err) {
                showToast('Ошибка соединения с сервером', 'danger');
            } finally {
                if (submitButton && !submitButton.disabled) {
                    submitButton.disabled = false;
                }
            }
        });
    }

    // 4. Система всплывающих уведомлений (Toast)
    window.showToast = function(message, type = 'info', duration = 4000) {
        const container = document.getElementById('toast-container') || document.createElement('div');
        if (!document.getElementById('toast-container')) {
            container.id = 'toast-container';
            container.className = 'toast-container';
            document.body.appendChild(container);
        }

        const toastEl = document.createElement('div');
        toastEl.className = `toast align-items-center text-white bg-${type} border-0 show`;
        toastEl.setAttribute('role', 'alert');
        toastEl.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>`;
        container.appendChild(toastEl);
        setTimeout(() => toastEl.remove(), duration);
    };

    // 5. Прогрессивное улучшение: автофокус на первом поле ошибки валидации
    const firstError = document.querySelector('.is-invalid');
    if (firstError) firstError.focus();
});
