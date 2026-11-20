// Presentación progresiva: el servidor mantiene las validaciones y la transacción.
// Cada línea eliminada se marca con DELETE oculto para preservar el formset Django.
(() => {
  const contenedor = document.getElementById('lineas');
  const agregar = document.getElementById('agregar');
  const total = document.getElementById('id_lineas-TOTAL_FORMS');
  const plantilla = document.getElementById('linea-vacia');
  if (!contenedor || !agregar || !total || !plantilla) return;

  const filasVisibles = () => [...contenedor.querySelectorAll('[data-linea]:not([hidden])')];

  function actualizarFilas() {
    const filas = filasVisibles();
    filas.forEach((fila, i) => {
      fila.querySelector('.detalle-nombre').textContent = `Producto ${i + 1}`;
      fila.querySelector('[data-quitar]').hidden = filas.length <= 1;
    });
    agregar.disabled = Number(total.value) >= 100;
  }

  agregar.addEventListener('click', () => {
    const indice = Number(total.value);
    if (!Number.isInteger(indice) || indice >= 100) return;
    contenedor.insertAdjacentHTML('beforeend', plantilla.innerHTML.replaceAll('__prefix__', String(indice)));
    total.value = indice + 1;
    actualizarFilas();
    const nueva = filasVisibles().at(-1);
    nueva?.querySelector('select[name$="-producto"]')?.focus();
  });

  contenedor.addEventListener('click', (evento) => {
    const boton = evento.target.closest('[data-quitar]');
    if (!boton || filasVisibles().length <= 1) return;
    const fila = boton.closest('[data-linea]');
    const marca = fila?.querySelector('input[name$="-DELETE"]');
    if (!marca) return;
    marca.value = 'on';
    fila.hidden = true;
    actualizarFilas();
  });

  contenedor.addEventListener('change', (evento) => {
    if (!evento.target.matches('select[name$="-producto"]')) return;
    const precios = document.getElementById('precios');
    if (!precios) return;
    const opcion = [...precios.options].find(o => o.value === evento.target.value);
    const precio = evento.target.closest('[data-linea]')?.querySelector('[name$="-precio_unitario"]');
    if (opcion && precio) precio.value = opcion.dataset.precio;
  });

  actualizarFilas();
})();
