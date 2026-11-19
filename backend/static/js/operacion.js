// Mejora progresiva; el servidor valida todos los datos y recalcula los importes.
const total = document.getElementById('id_lineas-TOTAL_FORMS');
document.getElementById('agregar').addEventListener('click', () => {
  const indice = Number(total.value);
  if (indice >= 100) return;
  const html = document.getElementById('linea-vacia').innerHTML.replaceAll('__prefix__', indice);
  document.getElementById('lineas').insertAdjacentHTML('beforeend', html);
  total.value = indice + 1;
});
document.getElementById('lineas').addEventListener('change', (evento) => {
  if (!evento.target.name.endsWith('-producto')) return;
  const opcion = document.querySelector(`#precios option[value="${evento.target.value}"]`);
  const precio = evento.target.closest('.detalle').querySelector('[name$="-precio_unitario"]');
  if (opcion && precio) precio.value = opcion.dataset.precio;
});
