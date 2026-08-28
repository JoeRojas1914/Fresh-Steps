(function () {

    const reqCounters = new WeakMap();

    async function cargarTablaAjax(url, container, { push = true } = {}) {
        const myId = (reqCounters.get(container) || 0) + 1;
        reqCounters.set(container, myId);

        const fetchUrl = new URL(url, window.location.href);
        fetchUrl.searchParams.set('partial', '1');

        container.style.opacity = '0.5';
        container.style.pointerEvents = 'none';

        try {
            const resp = await fetch(fetchUrl.toString());
            if (!resp.ok) throw new Error(resp.status);
            const html = await resp.text();

            if (reqCounters.get(container) !== myId) return;

            container.innerHTML = html;
            if (push) history.pushState(null, '', url);
            if (window.lucide) window.lucide.createIcons();
        } catch {
            if (reqCounters.get(container) === myId) window.location.href = url;
        } finally {
            if (reqCounters.get(container) === myId) {
                container.style.opacity = '';
                container.style.pointerEvents = '';
                const loader = document.getElementById('page-loader');
                if (loader) {
                    loader.className = 'is-done';
                    setTimeout(() => { loader.className = ''; }, 500);
                }
            }
        }
    }

    function initFiltroAjax(form, container, { debounceMs = 300, clearEl = null } = {}) {
        if (!form || !container) return;

        function buildUrl() {
            const params = new URLSearchParams(new FormData(form));
            for (const [k, v] of [...params.entries()]) {
                if (!v) params.delete(k);
            }
            const qs = params.toString();
            return qs ? `${form.action}?${qs}` : form.action;
        }

        let debounceTimer = null;

        function buscarInmediato() {
            clearTimeout(debounceTimer);
            cargarTablaAjax(buildUrl(), container);
        }

        function buscarConDebounce() {
            clearTimeout(debounceTimer);
            debounceTimer = setTimeout(() => cargarTablaAjax(buildUrl(), container), debounceMs);
        }

        form.querySelectorAll('input[type=text], input[type=number], input[type=search]').forEach(el => {
            el.addEventListener('input', buscarConDebounce);
        });

        form.querySelectorAll('select, input[type=date], input[type=checkbox], input[type=radio]').forEach(el => {
            el.addEventListener('change', buscarInmediato);
        });

        form.addEventListener('submit', (e) => {
            e.preventDefault();
            buscarInmediato();
        });

        if (clearEl) {
            clearEl.addEventListener('click', (e) => {
                e.preventDefault();
                form.querySelectorAll('input[type=text], input[type=number], input[type=date], input[type=search]').forEach(el => { el.value = ''; });
                form.querySelectorAll('select').forEach(el => { el.selectedIndex = 0; });
                form.querySelectorAll('input[type=checkbox], input[type=radio]').forEach(el => { el.checked = false; });
                cargarTablaAjax(clearEl.href || form.action, container);
            });
        }
    }

    document.addEventListener('click', function (e) {
        const link = e.target.closest('.paginacion a');
        if (!link) return;

        const container = document.getElementById('tabla-paginada');
        if (!container) return;

        e.preventDefault();
        cargarTablaAjax(link.href, container);
    });

    window.cargarTablaAjax = cargarTablaAjax;
    window.initFiltroAjax  = initFiltroAjax;
})();
