(function () {
  'use strict';

  const form    = document.getElementById('form-filtro-pagos');
  const destino = document.getElementById('tabla-paginada');

  window.initFiltroAjax(form, destino);
}());
