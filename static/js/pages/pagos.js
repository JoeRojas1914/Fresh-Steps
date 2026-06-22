(function () {
  'use strict';

  const form     = document.getElementById('form-filtro-pagos');
  const btnClear = document.getElementById('btn-limpiar-filtro');
  const destino  = document.getElementById('tabla-paginada');
  const base     = window.location.pathname;

  function buildUrl(params) {
    const qs = new URLSearchParams(params).toString();
    return qs ? base + '?' + qs : base;
  }

  function cargarTabla(url, pushUrl) {
    const fetchUrl = url.includes('?')
      ? url + '&partial=1'
      : url + '?partial=1';

    fetch(fetchUrl, { headers: { 'X-Requested-With': 'XMLHttpRequest' } })
      .then(function (r) { return r.text(); })
      .then(function (html) {
        destino.innerHTML = html;
        if (pushUrl) history.pushState({}, '', pushUrl);
        if (typeof lucide !== 'undefined') lucide.createIcons();
      })
      .finally(function () {
        var loader = document.getElementById('page-loader');
        if (loader) {
          loader.className = 'is-done';
          setTimeout(function () { loader.className = ''; }, 500);
        }
      });
  }

  if (form) {
    form.addEventListener('submit', function (e) {
      e.preventDefault();
      const data = new FormData(form);
      const params = {};
      data.forEach(function (v, k) { if (v) params[k] = v; });
      const url = buildUrl(params);
      cargarTabla(url, url);
    });
  }

  if (btnClear) {
    btnClear.addEventListener('click', function (e) {
      e.preventDefault();
      if (form) form.querySelectorAll('select, input').forEach(function (el) {
        if (el.tagName === 'SELECT') el.value = '';
        else el.value = '';
      });
      cargarTabla(base, base);
    });
  }
}());
