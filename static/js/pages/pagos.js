(function () {
  'use strict';

  const form    = document.getElementById('form-filtro-pagos');
  const clearEl = document.getElementById('btn-limpiar-filtro');
  const destino = document.getElementById('tabla-paginada');

  window.initFiltroAjax(form, destino, { clearEl });
}());
