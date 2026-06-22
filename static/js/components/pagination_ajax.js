(function () {
    document.addEventListener('click', async function (e) {
        const link = e.target.closest('.paginacion a');
        if (!link) return;

        const container = document.getElementById('tabla-paginada');
        if (!container) return;

        e.preventDefault();

        const url = new URL(link.href, window.location.href);
        url.searchParams.set('partial', '1');

        container.style.opacity = '0.5';
        container.style.pointerEvents = 'none';

        try {
            const resp = await fetch(url.toString());
            if (!resp.ok) throw new Error(resp.status);
            const html = await resp.text();
            container.innerHTML = html;
            history.pushState(null, '', link.href);
            if (window.lucide) window.lucide.createIcons();
        } catch {
            window.location.href = link.href;
        } finally {
            container.style.opacity = '';
            container.style.pointerEvents = '';
            const loader = document.getElementById('page-loader');
            if (loader) {
                loader.className = 'is-done';
                setTimeout(() => { loader.className = ''; }, 500);
            }
        }
    });
})();
